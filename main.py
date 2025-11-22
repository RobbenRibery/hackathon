import asyncio
import logging
import os
from dotenv import load_dotenv
from synapse.router import Router
from synapse.agent import NegotiationAgent

# Load environment variables
load_dotenv(override=True)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    datefmt='%H:%M:%S'
)

async def main(sell_agent_config: dict, buy_agent_config: dict, initial_offer: dict):
    print("=== Synapse Protocol: Negotiation Demo ===\n")
    
    # Create the router (message bus)
    router = Router()
    
    # Create two agents with different goals
    seller = NegotiationAgent(router=router, **sell_agent_config)
    buyer = NegotiationAgent(router=router, **buy_agent_config)
    
    print(f"✓ Created agents: {seller.card.name} and {buyer.card.name}")
    print(f"✓ Registered agents: {router.list_agents()}\n")
    
    print(">>> Starting Negotiation...\n")
    await seller.start_conversation("buyer_agent", initial_offer)
    
    # Keep the script running to let them negotiate
    await asyncio.sleep(30) # Increased time for LLM latency
    
    print("\n=== Negotiation Complete ===")
    print(f"Total messages exchanged: {len(seller.history) + len(buyer.history)}")

if __name__ == "__main__":
    # Use gpt-4o-mini for both agents
    model_name = "openai:gpt-4o-mini"
    
    seller_config = {
        "id": "seller_agent",
        "name": "Seller",
        "system_prompt": "You are a seller of a vintage Leica M3 camera. You want to sell it for at least $1800. You are tough but fair.",
        "model_name": model_name
    }
    
    buyer_config = {
        "id": "buyer_agent",
        "name": "Buyer",
        "system_prompt": "You are a buyer looking for a Leica M3. Your budget is $1500, but you can go up to $1650 for a good condition one.",
        "model_name": model_name
    }
    
    initial_offer = {
        "topic": "buy_leica_m3",
        "terms": {
            "price": 1800,
            "currency": "USD",
            "condition": "Excellent"
        }
    }
    
    asyncio.run(main(seller_config, buyer_config, initial_offer))
