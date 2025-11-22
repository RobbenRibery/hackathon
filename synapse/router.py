import asyncio
import logging
from typing import Dict, Callable, Coroutine, Any, List
from .protocol import Message

logger = logging.getLogger("synapse.router")

class Router:
    """
    A central message router that connects agents.
    It handles registration, discovery, and message delivery.
    """
    def __init__(self):
        self.agents: Dict[str, Callable[[Message], Coroutine[Any, Any, None]]] = {}

    def register(self, agent_id: str, handler: Callable[[Message], Coroutine[Any, Any, None]]):
        """Registers an agent with its message handler."""
        self.agents[agent_id] = handler
        logger.info(f"Registered agent: {agent_id}")

    def unregister(self, agent_id: str):
        """Unregisters an agent."""
        if agent_id in self.agents:
            del self.agents[agent_id]
            logger.info(f"Unregistered agent: {agent_id}")

    def list_agents(self) -> List[str]:
        """Returns a list of registered agent IDs."""
        return list(self.agents.keys())

    async def send(self, message: Message):
        """
        Routes a message to the target agent.
        """
        if message.to_agent not in self.agents:
            logger.error(f"Delivery failed: Agent {message.to_agent} not found.")
            return
        
        logger.info(f"Routing message: {message.from_agent} -> {message.to_agent} [{message.type}]")
        
        # Simulate network latency
        await asyncio.sleep(0.05) 
        
        target_handler = self.agents[message.to_agent]
        
        # Use create_task to decouple the sender from the receiver's processing
        # This prevents infinite recursion depth when agents reply immediately
        asyncio.create_task(target_handler(message))
