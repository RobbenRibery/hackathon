import asyncio
import logging
from typing import List, Dict, Any, Optional, Literal
from pydantic import BaseModel
from .protocol import Message, MessagePayload, AgentCard
from .router import Router

# Configure logging
logger = logging.getLogger("synapse.agent")

# Try to import pydantic_ai
try:
    from pydantic_ai import Agent as PydanticAgent
    PYDANTIC_AI_AVAILABLE = True
except ImportError:
    PYDANTIC_AI_AVAILABLE = False
    PydanticAgent = None

class AgentResponse(BaseModel):
    """Structured response expected from the LLM Agent."""
    type: Literal["PROPOSAL", "REJECTION", "ACCEPTANCE", "COMMITMENT", "INFO"]
    reasoning: str
    payload: MessagePayload

class NegotiationAgent:
    """
    An autonomous agent participating in the negotiation.
    It uses pydantic-ai to generate responses based on conversation history.
    """
    def __init__(
        self, 
        id: str, 
        name: str, 
        router: Router, 
        system_prompt: str, 
        model_name: str = "gemini-1.5-flash",
        **config
    ):
        self.card = AgentCard(id=id, name=name, capabilities=["negotiation"])
        self.router = router
        self.system_prompt = system_prompt
        self.model_name = model_name
        self.history: List[Message] = []
        
        # Register self with the router
        self.router.register(id, self.receive)
        
        self.ai_agent = None
        
        if PYDANTIC_AI_AVAILABLE and PydanticAgent:
            # Create the PydanticAI Agent with a system prompt defining its persona and goal
            self.ai_agent = PydanticAgent(
                model_name,
                output_type=AgentResponse,
                system_prompt=f"You are an autonomous agent named {name}.\nYour Goal: {system_prompt}"
            )
        else:
            logger.warning(f"[{name}] pydantic_ai not available. Using mock logic.")

    async def receive(self, message: Message):
        """
        Callback for receiving messages from the Router.
        """
        # Add to history
        self.history.append(message)
        
        logger.info(f"[{self.card.name}] Received {message.type} from {message.from_agent}")
        
        # Don't reply to self
        if message.from_agent == self.card.id:
            return

        # Stop condition for the demo to prevent infinite loops
        if message.type in ["ACCEPTANCE", "COMMITMENT"]:
            logger.info(f"[{self.card.name}] Agreement reached or conversation ended.")
            return
        
        if message.type == "INFO":
            logger.info(f"[{self.card.name}] Acknowledged info.")
            return

        # Process the message
        await self.think_and_reply(message)

    async def think_and_reply(self, incoming_message: Message):
        """
        Analyzes the incoming message and generates a response using LLM or Mock logic.
        """
        if self.ai_agent:
            # Construct prompt with conversation context
            prompt = self._construct_prompt(incoming_message)
            
            # Run the agent (this call invokes the LLM)
            result = await self.ai_agent.run(prompt)
            response_data = result.data
            
            # Create the response message
            reply = Message(
                from_agent=self.card.id,
                to_agent=incoming_message.from_agent,
                thread_id=incoming_message.thread_id,
                type=response_data.type,
                payload=response_data.payload,
                reasoning=response_data.reasoning
            )
            
            self.history.append(reply)
            await self.router.send(reply)
        else:
            # Fallback for when pydantic_ai is not available or initialized
            await self._send_mock_response(incoming_message)

    def _construct_prompt(self, incoming_message: Message) -> str:
        """
        Builds the context string for the LLM.
        """
        return f"""
        Current Conversation History:
        {self._format_history()}
        
        The last message was from {incoming_message.from_agent}:
        Type: {incoming_message.type}
        Reasoning: {incoming_message.reasoning}
        Payload: {incoming_message.payload.model_dump_json()}
        
        Decide on the next strategic move. Respond with the appropriate action type and payload.
        """

    async def _send_mock_response(self, incoming_message: Message):
        """
        Simple rule-based logic for testing without an LLM.
        """
        response_data = self._mock_logic()
        
        # If mock logic returns None (shouldn't happen with current logic but good for safety)
        if not response_data:
            return

        reply = Message(
            from_agent=self.card.id,
            to_agent=incoming_message.from_agent,
            thread_id=incoming_message.thread_id,
            type=response_data["type"],
            payload=MessagePayload(**response_data["payload"]),
            reasoning=response_data["reasoning"]
        )
        
        logger.info(f"[{self.card.name}] Sending mock response: {reply.type}")
        self.history.append(reply)
        await self.router.send(reply)

    def _mock_logic(self) -> Dict[str, Any]:
        last_msg = self.history[-1]
        if last_msg.type == "PROPOSAL":
            return {
                "type": "REJECTION",
                "reasoning": "Mock Agent: Price too high.",
                "payload": {"counter_offer": {"price": 90}}
            }
        elif last_msg.type == "REJECTION":
             return {
                "type": "ACCEPTANCE",
                "reasoning": "Mock Agent: Agreed.",
                "payload": {"final_terms": {"price": 90}}
            }
        # Default fallback
        return {"type": "INFO", "reasoning": "I am listening.", "payload": {}}

    def _format_history(self) -> str:
        """Formats the last few messages for context window efficiency."""
        # Take last 10 messages to provide decent context
        recent = self.history[-10:]
        return "\n".join([f"{m.from_agent} -> {m.to_agent} [{m.type}]: {m.reasoning}" for m in recent])

    async def start_conversation(self, to_agent: str, initial_proposal: Dict[str, Any]):
        """
        Initiates a conversation with another agent.
        """
        logger.info(f"[{self.card.name}] Starting conversation with {to_agent}")
        msg = Message(
            from_agent=self.card.id,
            to_agent=to_agent,
            type="PROPOSAL",
            payload=MessagePayload(**initial_proposal),
            reasoning="Initiating negotiation."
        )
        self.history.append(msg)
        await self.router.send(msg)
