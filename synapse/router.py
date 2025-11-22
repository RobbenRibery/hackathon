import asyncio
from typing import Dict, Callable, Coroutine, Any
from .protocol import Message

class Router:
    def __init__(self):
        self.agents: Dict[str, Callable[[Message], Coroutine[Any, Any, None]]] = {}

    def register(self, agent_id: str, handler: Callable[[Message], Coroutine[Any, Any, None]]):
        self.agents[agent_id] = handler
        print(f"[Router] Registered agent: {agent_id}")

    async def send(self, message: Message):
        if message.to_agent not in self.agents:
            print(f"[Router] Error: Agent {message.to_agent} not found.")
            return
        
        print(f"[Router] Routing message from {message.from_agent} to {message.to_agent} (Type: {message.type})")
        # Simulate network latency
        await asyncio.sleep(0.1) 
        await self.agents[message.to_agent](message)
