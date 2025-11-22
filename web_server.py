"""
FastAPI Web Server for BUYER/SELLER configuration and negotiation execution
"""
import asyncio
import json
import logging
from pathlib import Path
from typing import Dict, Any, Optional
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel
from synapse.router import Router
from synapse.agent import NegotiationAgent
from synapse.protocol import Message, MessagePayload
from synapse.schemas import BuyerSchema, SellerSchema
from synapse.config_loader import load_buyer_config, load_seller_config, build_system_prompt_from_schema

# Load environment variables (for OPENAI_API_KEY)
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="Negotiation Agent WebUI")

# Enable CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global state
router = Router()
active_negotiations: Dict[str, Dict[str, Any]] = {}
buyer_agent: Optional[NegotiationAgent] = None
seller_agent: Optional[NegotiationAgent] = None

# Request/Response models
class NegotiationStartRequest(BaseModel):
    listed_price: float
    product_title: str = "Product"

class NegotiationRoundRequest(BaseModel):
    negotiation_id: str

# Serve static files
static_dir = Path("webui")
if static_dir.exists():
    app.mount("/static", StaticFiles(directory=static_dir), name="static")

@app.get("/")
async def index():
    """Serve the main WebUI page"""
    webui_file = Path("webui/index.html")
    if webui_file.exists():
        return FileResponse(webui_file)
    return {"message": "WebUI not found. Please create webui/index.html"}

@app.get("/api/buyer")
async def get_buyer_config():
    """Get current buyer configuration"""
    config = load_buyer_config()
    return config.model_dump()

@app.put("/api/buyer")
async def update_buyer_config(config: Dict[str, Any]):
    """Update buyer configuration"""
    try:
        buyer_schema = BuyerSchema(**config)
        config_path = Path("config/buyer.json")
        config_path.parent.mkdir(parents=True, exist_ok=True)
        with open(config_path, 'w') as f:
            json.dump(buyer_schema.model_dump(), f, indent=2)
        return buyer_schema.model_dump()
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.get("/api/seller")
async def get_seller_config():
    """Get current seller configuration"""
    config = load_seller_config()
    return config.model_dump()

@app.put("/api/seller")
async def update_seller_config(config: Dict[str, Any]):
    """Update seller configuration"""
    try:
        seller_schema = SellerSchema(**config)
        config_path = Path("config/seller.json")
        config_path.parent.mkdir(parents=True, exist_ok=True)
        with open(config_path, 'w') as f:
            json.dump(seller_schema.model_dump(), f, indent=2)
        return seller_schema.model_dump()
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.post("/api/negotiation/start")
async def start_negotiation(request: NegotiationStartRequest):
    """Start a new negotiation between buyer and seller"""
    global buyer_agent, seller_agent
    
    try:
        logger.info(f"Starting negotiation: {request.product_title} @ ${request.listed_price}")
        
        # Load configurations
        buyer_config = load_buyer_config()
        seller_config = load_seller_config()
        
        # Build system prompts
        buyer_prompt = build_system_prompt_from_schema(buyer_config, "buyer")
        seller_prompt = build_system_prompt_from_schema(seller_config, "seller")
        
        # Create new router and agents
        router = Router()
        buyer_agent = NegotiationAgent(
            id="buyer_agent",
            name="Buyer",
            router=router,
            system_prompt=buyer_prompt,
            model_name="openai:gpt-4o-mini" if buyer_config.useLLM else None
        )
        seller_agent = NegotiationAgent(
            id="seller_agent",
            name="Seller",
            router=router,
            system_prompt=seller_prompt,
            model_name="openai:gpt-4o-mini" if seller_config.useLLM else None
        )
        
        logger.info("Agents created successfully")
        
        # Create negotiation ID
        negotiation_id = f"neg_{len(active_negotiations) + 1}"
        
        # Start conversation
        initial_offer = {
            "topic": request.product_title,
            "terms": {
                "price": request.listed_price,
                "currency": "USD"
            }
        }
        
        logger.info("Starting conversation from seller...")
        await seller_agent.start_conversation("buyer_agent", initial_offer)
        
        # Wait for initial response from buyer (agents respond asynchronously)
        logger.info("Waiting for buyer response...")
        await asyncio.sleep(2.0)
        
        # Get messages
        all_messages = buyer_agent.history + seller_agent.history
        all_messages.sort(key=lambda m: m.timestamp)
        
        logger.info(f"Total messages after start: {len(all_messages)}")
        
        # Store negotiation
        active_negotiations[negotiation_id] = {
            "id": negotiation_id,
            "buyer_agent": buyer_agent,
            "seller_agent": seller_agent,
            "router": router,
            "listed_price": request.listed_price,
            "product_title": request.product_title,
            "messages": [_message_to_dict(m) for m in all_messages],
            "round_number": len([m for m in all_messages if m.type in ["PROPOSAL", "REJECTION"]]),
            "status": "active"
        }
        
        return {
            "negotiation_id": negotiation_id,
            "messages": active_negotiations[negotiation_id]["messages"],
            "status": "active"
        }
    except Exception as e:
        logger.error(f"Error starting negotiation: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/negotiation/round")
async def run_negotiation_round(request: NegotiationRoundRequest):
    """Run one round of negotiation"""
    try:
        logger.info(f"Running round for negotiation: {request.negotiation_id}")
        
        if request.negotiation_id not in active_negotiations:
            raise HTTPException(status_code=404, detail="Negotiation not found")
        
        neg = active_negotiations[request.negotiation_id]
        
        if neg["status"] != "active":
            raise HTTPException(status_code=400, detail="Negotiation is not active")
        
        buyer = neg["buyer_agent"]
        seller = neg["seller_agent"]
        
        # Get current state
        all_messages_before = buyer.history + seller.history
        all_messages_before.sort(key=lambda m: m.timestamp)
        
        if not all_messages_before:
            raise HTTPException(status_code=400, detail="No messages in negotiation")
        
        last_msg = all_messages_before[-1]
        logger.info(f"Last message from: {last_msg.from_agent}, type: {last_msg.type}")
        
        # Determine who should respond next
        # If last message was from seller, buyer should respond (and vice versa)
        if last_msg.from_agent == seller.card.id:
            # Buyer should respond
            logger.info("Triggering buyer response...")
            continuation_msg = Message(
                from_agent="system",
                to_agent=buyer.card.id,
                thread_id=last_msg.thread_id,
                type="INFO",
                payload=MessagePayload(content="Please continue the negotiation based on the seller's last message."),
                reasoning="System: Continue negotiation"
            )
            await buyer.receive(continuation_msg)
        elif last_msg.from_agent == buyer.card.id:
            # Seller should respond
            logger.info("Triggering seller response...")
            continuation_msg = Message(
                from_agent="system",
                to_agent=seller.card.id,
                thread_id=last_msg.thread_id,
                type="INFO",
                payload=MessagePayload(content="Please continue the negotiation based on the buyer's last message."),
                reasoning="System: Continue negotiation"
            )
            await seller.receive(continuation_msg)
        else:
            # System message or unknown - determine from message count
            buyer_msg_count = len([m for m in all_messages_before if m.from_agent == buyer.card.id])
            seller_msg_count = len([m for m in all_messages_before if m.from_agent == seller.card.id])
            if buyer_msg_count <= seller_msg_count:
                # Buyer should respond
                logger.info("Triggering buyer response (by count)...")
                continuation_msg = Message(
                    from_agent="system",
                    to_agent=buyer.card.id,
                    thread_id=last_msg.thread_id,
                    type="INFO",
                    payload=MessagePayload(content="Please continue the negotiation."),
                    reasoning="System: Continue negotiation"
                )
                await buyer.receive(continuation_msg)
            else:
                # Seller should respond
                logger.info("Triggering seller response (by count)...")
                continuation_msg = Message(
                    from_agent="system",
                    to_agent=seller.card.id,
                    thread_id=last_msg.thread_id,
                    type="INFO",
                    payload=MessagePayload(content="Please continue the negotiation."),
                    reasoning="System: Continue negotiation"
                )
                await seller.receive(continuation_msg)
        
        # Wait for response to be generated and sent
        logger.info("Waiting for agent response...")
        await asyncio.sleep(2.0)
        
        # Get updated messages
        all_messages = buyer.history + seller.history
        all_messages.sort(key=lambda m: m.timestamp)
        
        logger.info(f"Total messages after round: {len(all_messages)}")
        
        # Update negotiation
        neg["messages"] = [_message_to_dict(m) for m in all_messages]
        neg["round_number"] = len([m for m in all_messages if m.type in ["PROPOSAL", "REJECTION"]])
        
        # Check if negotiation is complete
        if all_messages:
            last_msg = all_messages[-1]
            if last_msg.type in ["ACCEPTANCE", "COMMITMENT"]:
                neg["status"] = "completed"
                logger.info("Negotiation completed!")
            elif neg["round_number"] >= max(load_buyer_config().maxRounds, load_seller_config().maxRounds):
                neg["status"] = "aborted"
                logger.info("Negotiation aborted - max rounds reached")
        
        return {
            "negotiation_id": request.negotiation_id,
            "messages": neg["messages"],
            "round_number": neg["round_number"],
            "status": neg["status"]
        }
    except Exception as e:
        logger.error(f"Error running negotiation round: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/negotiation/{negotiation_id}")
async def get_negotiation(negotiation_id: str):
    """Get negotiation status"""
    if negotiation_id not in active_negotiations:
        raise HTTPException(status_code=404, detail="Negotiation not found")
    
    neg = active_negotiations[negotiation_id]
    buyer = neg["buyer_agent"]
    seller = neg["seller_agent"]
    
    # Get latest messages
    all_messages = buyer.history + seller.history
    all_messages.sort(key=lambda m: m.timestamp)
    neg["messages"] = [_message_to_dict(m) for m in all_messages]
    
    return neg

def _message_to_dict(message: Message) -> Dict[str, Any]:
    """Convert Message to dict"""
    price = None
    if message.payload.terms and "price" in message.payload.terms:
        price = message.payload.terms["price"]
    elif message.payload.counter_offer and "price" in message.payload.counter_offer:
        price = message.payload.counter_offer["price"]
    elif message.payload.final_terms and "price" in message.payload.final_terms:
        price = message.payload.final_terms["price"]
    
    content = message.payload.content or message.reasoning
    
    return {
        "id": message.id,
        "from": message.from_agent,
        "to": message.to_agent,
        "timestamp": message.timestamp.isoformat(),
        "type": message.type,
        "reasoning": message.reasoning,
        "content": content,
        "price": price,
        "role": "buyer" if "buyer" in message.from_agent.lower() else "seller"
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)

