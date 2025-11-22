import asyncio
import logging
import json
from synapse.router import Router
from synapse.agent import NegotiationAgent
from pydantic import BaseModel, Field
from textwrap import dedent

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    datefmt='%H:%M:%S'
)

def load_settings(filepath: str) -> dict:
    """Extracts default values from the JSON schema."""
    try:
        with open(filepath, 'r') as f:
            schema = json.load(f)
        
        settings = {}
        if "properties" in schema:
            for key, value in schema["properties"].items():
                if "default" in value:
                    settings[key] = value["default"]
        return settings
    except Exception as e:
        logging.error(f"Failed to load settings: {e}")
        return {}

class Output(BaseModel):
    messages:list[dict] = Field(description="Messages exchanged between the agents.")
    prices:list[dict] = Field(description="Prices exchanged between the agents.")
    justification:str = Field(description="Justification for the prices exchanged between the agents.")

    @property
    def final_price(self) -> float:
        return self.prices[-1]["price"]

async def main(sell_agent_config: dict, buy_agent_config: dict, initial_offer: dict) -> dict:
    print("=== Synapse Protocol: Negotiation Demo ===\n")
    
    # Create the router (message bus)
    router = Router()
    
    # Create two agents with different goals
    seller = NegotiationAgent(router=router, **sell_agent_config)
    buyer = NegotiationAgent(router=router, **buy_agent_config)
    
    print(f"✓ Created agents: {seller.card.name} and {buyer.card.name}")
    print(f"✓ Registered agents: {router.list_agents()}\n")

    if input("Do you want to start the negotiation? (y/n)") != "y":
        exit()
    
    print(">>> Starting Negotiation...\n")
    await seller.start_conversation("buyer_agent", initial_offer)
    
    # Keep the script running to let them negotiate
    # Using a longer timeout to allow for delays and multiple rounds
    await asyncio.sleep(120) 
    
    print("\n=== Negotiation Complete ===")
    print(f"Total messages exchanged: {len(seller.history) + len(buyer.history)}")


if __name__ == "__main__":
    
    # Use gpt-4o-mini for both agents
    model_name = "openai:gpt-4o-mini"
    
    # Load settings
    seller_settings = load_settings("negotiation_settings_seller.json")
    buyer_settings = load_settings("negotiation_settings_buyer.json")
    
    buyer_config = {
        "id": "buyer_agent",
        "name": "Buyer",
        "system_prompt": "You are a buyer looking for a Leica M3. Your budget is $1500, but you can go up to $1650 for a good condition one.",
        "model_name": model_name,
        **settings # Squash settings into config
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
