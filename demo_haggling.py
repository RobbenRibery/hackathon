import asyncio
import os
from synapse.router import Router
from synapse.agent import Agent

async def main(sell_agent_config:dict, buy_agent_config:dict):
    print("--- Synapse Protocol: Haggling Demo ---")
    router = Router()
    sell_agent_config['router'] = router
    buy_agent_config['router'] = router
    seller = Agent(**sell_agent_config)
    buyer = Agent(**buy_agent_config)
    
    # 3. Start the conversation
    initial_offer = {
        "topic": "buy_leica_m3",
        "terms": {
            "price": 1800,
            "currency": "USD",
            "condition": "Excellent"
        }
    }
    
    print("\n>>> Starting Negotiation...")
    await seller.start_conversation("buyer_agent", initial_offer)
    
    # Keep the script running for a bit to let them talk
    await asyncio.sleep(10)
    print("\n>>> Demo Finished (Timeout)")

if __name__ == "__main__":
    seller_config = {
        "id": "seller_agent",
        "name": "Seller",
        "router": None, 
        "system_prompt": "You are a seller of a vintage Leica M3 camera. You want to sell it for at least $1800. You are tough but fair."
    }
    
    buyer_config = {
        "id": "buyer_agent",
        "name": "Buyer",
        "router": None,
        "system_prompt": "You are a buyer looking for a Leica M3. Your budget is $1500, but you can go up to $1650 for a good condition one."
    }
    
    asyncio.run(main(seller_config, buyer_config))
