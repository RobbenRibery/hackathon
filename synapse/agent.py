import asyncio
import os
import json
from typing import List, Dict, Any, Literal
from pydantic import BaseModel, Field
from .protocol import Message, MessagePayload, AgentCard
from .router import Router

# Try to import pydantic_ai, handle if missing
from pydantic_ai import Agent

class AgentResponse(BaseModel):
    type: Literal["PROPOSAL", "REJECTION", "ACCEPTANCE", "COMMITMENT", "INFO"]
    reasoning: str
    payload: MessagePayload

class Agent:
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
        self.router.register(id, self.receive)
        
        self.ai_agent = None
        # Create the PydanticAI Agent
        # We inject the system prompt here
        self.ai_agent = Agent(
            model_name,
            result_type=AgentResponse,
            system_prompt=f"You are an autonomous agent named {name}.\nYour Goal: {system_prompt}"
        )

    async def receive(self, message: Message):
        self.history.append(message)
        print(f"\n--- {self.card.name} received message from {message.from_agent} ---")
        print(f"Type: {message.type}")
        print(f"Reasoning: {message.reasoning}")
        print(f"Payload: {message.payload}")
        
        # Don't reply to self or INFO messages that don't require action (simplification)
        if message.from_agent == self.card.id:
            return

        # Decide what to do
        await self.think_and_reply(message)

    async def think_and_reply(self, incoming_message: Message):
        if self.ai_agent:
            try:
                # Construct prompt with history
                # We pass the conversation history as the user prompt context
                prompt = f"""
                Current Conversation History:
                {self._format_history()}
                
                The last message was from {incoming_message.from_agent}:
                Type: {incoming_message.type}
                Reasoning: {incoming_message.reasoning}
                Payload: {incoming_message.payload.model_dump_json()}
                
                Respond with the appropriate action.
                """
                
                # Run the agent
                result = await self.ai_agent.run(prompt)
                response_data = result.data
                
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
                
            except Exception as e:
                print(f"[{self.card.name}] Error in AI processing: {e}")
                # Fallback or retry logic could go here
        else:
            # Mock response
            await self._send_mock_response(incoming_message)

    async def _send_mock_response(self, incoming_message: Message):
        # Simple heuristic mock for demo purposes if no API key
        response_data = self._mock_logic()
        
        reply = Message(
            from_agent=self.card.id,
            to_agent=incoming_message.from_agent,
            thread_id=incoming_message.thread_id,
            type=response_data["type"],
            payload=MessagePayload(**response_data["payload"]),
            reasoning=response_data["reasoning"]
        )
        
        self.history.append(reply)
        await self.router.send(reply)

    def _mock_logic(self) -> Dict[str, Any]:
        last_msg = self.history[-1]
        if last_msg.type == "PROPOSAL":
            return {
                "type": "REJECTION",
                "reasoning": "I am a mock agent and I always reject the first offer.",
                "payload": {"counter_offer": {"price": 90}}
            }
        elif last_msg.type == "REJECTION":
             return {
                "type": "ACCEPTANCE",
                "reasoning": "Okay, I accept your counter offer.",
                "payload": {"final_terms": {"price": 90}}
            }
        return {"type": "INFO", "reasoning": "I don't know what to do.", "payload": {}}

    def _format_history(self) -> str:
        return "\n".join([f"{m.from_agent} -> {m.to_agent} [{m.type}]: {m.reasoning}" for m in self.history[-5:]])

    async def start_conversation(self, to_agent: str, initial_proposal: Dict[str, Any]):
        msg = Message(
            from_agent=self.card.id,
            to_agent=to_agent,
            type="PROPOSAL",
            payload=MessagePayload(**initial_proposal),
            reasoning="Starting the negotiation."
        )
        self.history.append(msg)
        await self.router.send(msg)
