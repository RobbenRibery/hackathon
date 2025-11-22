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
        model_name: str = "openai:gpt-4o-mini",
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
            # Remove 'openai:' prefix if present, as pydantic-ai handles it automatically
            model = model_name.replace("openai:", "") if model_name.startswith("openai:") else model_name
            self.ai_agent = PydanticAgent(
                model,
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
        
        if message.type == "INFO" and message.from_agent != "system":
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
            
            # Access the output - pydantic-ai uses 'output' attribute
            # Log available attributes if output doesn't exist for debugging
            if not hasattr(result, 'output'):
                available_attrs = [a for a in dir(result) if not a.startswith('_')]
                logger.error(f"Result object has no 'output' attribute. Available: {available_attrs}")
                logger.error(f"Result type: {type(result)}, result value: {result}")
                raise AttributeError(f"AgentRunResult has no 'output' attribute. Available attributes: {available_attrs}")
            
            response_data = result.output
            
            # Determine who to send the reply to
            # If incoming message is from system, find the other agent
            to_agent = incoming_message.from_agent
            if to_agent == "system":
                # Find the other agent from history
                other_agent_messages = [m for m in self.history if m.from_agent != self.card.id and m.from_agent != "system"]
                if other_agent_messages:
                    to_agent = other_agent_messages[-1].from_agent
                else:
                    # Default: if we're buyer, send to seller and vice versa
                    to_agent = "seller_agent" if "buyer" in self.card.id else "buyer_agent"
            
            # Create the response message
            reply = Message(
                from_agent=self.card.id,
                to_agent=to_agent,
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
        # Handle system continuation messages
        if incoming_message.from_agent == "system":
            # Use the last actual message from the other agent to determine response
            other_agent_messages = [m for m in self.history if m.from_agent != self.card.id and m.from_agent != "system"]
            if not other_agent_messages:
                return
            last_other_msg = other_agent_messages[-1]
            # Process as if we received that message
            incoming_message = last_other_msg
        
        response_data = self._mock_logic()
        
        # If mock logic returns None (shouldn't happen with current logic but good for safety)
        if not response_data:
            return

        # Determine who to send to
        to_agent = incoming_message.from_agent if incoming_message.from_agent != "system" else None
        if not to_agent:
            # Find the other agent
            other_agent_messages = [m for m in self.history if m.from_agent != self.card.id and m.from_agent != "system"]
            if other_agent_messages:
                to_agent = other_agent_messages[-1].from_agent
            else:
                # Default: if we're buyer, send to seller and vice versa
                to_agent = "seller_agent" if "buyer" in self.card.id else "buyer_agent"

        reply = Message(
            from_agent=self.card.id,
            to_agent=to_agent,
            thread_id=incoming_message.thread_id,
            type=response_data["type"],
            payload=MessagePayload(**response_data["payload"]),
            reasoning=response_data["reasoning"]
        )
        
        logger.info(f"[{self.card.name}] Sending mock response: {reply.type}")
        self.history.append(reply)
        await self.router.send(reply)

    def _mock_logic(self) -> Dict[str, Any]:
        # Get the last non-system message
        last_msg = None
        for msg in reversed(self.history):
            if msg.from_agent != "system" and msg.from_agent != self.card.id:
                last_msg = msg
                break
        
        if not last_msg:
            # No message from other agent yet
            return {"type": "INFO", "reasoning": "Waiting for message.", "payload": {}}
        
        # Extract price from last message
        last_price = None
        if last_msg.payload.terms and "price" in last_msg.payload.terms:
            last_price = float(last_msg.payload.terms["price"])
        elif last_msg.payload.counter_offer and "price" in last_msg.payload.counter_offer:
            last_price = float(last_msg.payload.counter_offer["price"])
        elif last_msg.payload.final_terms and "price" in last_msg.payload.final_terms:
            last_price = float(last_msg.payload.final_terms["price"])
        
        if last_msg.type == "PROPOSAL":
            if last_price:
                # Counter with 10% discount
                counter_price = last_price * 0.9
                return {
                    "type": "REJECTION",
                    "reasoning": f"Thank you for the offer. Would you consider ${counter_price:.2f}?",
                    "payload": {"counter_offer": {"price": counter_price, "currency": "USD"}}
                }
            return {
                "type": "REJECTION",
                "reasoning": "I'd like to negotiate the price.",
                "payload": {"counter_offer": {}}
            }
        elif last_msg.type == "REJECTION":
            if last_price:
                # Check if we should accept or counter
                # For demo: accept if price is reasonable, otherwise counter
                if last_price <= 200:  # Accept if reasonable
                    return {
                        "type": "ACCEPTANCE",
                        "reasoning": f"${last_price:.2f} works for me. Let's proceed!",
                        "payload": {"final_terms": {"price": last_price, "currency": "USD"}}
                    }
                else:
                    # Counter with middle ground
                    counter_price = last_price * 0.95
                    return {
                        "type": "REJECTION",
                        "reasoning": f"I can do ${counter_price:.2f}. That's my best offer.",
                        "payload": {"counter_offer": {"price": counter_price, "currency": "USD"}}
                    }
            return {
                "type": "ACCEPTANCE",
                "reasoning": "I accept your terms.",
                "payload": {"final_terms": {}}
            }
        # Default fallback
        return {"type": "INFO", "reasoning": "I am considering your message.", "payload": {}}

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
