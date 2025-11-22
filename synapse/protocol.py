from typing import Optional, Dict, Any, List, Literal
from pydantic import BaseModel, Field
from datetime import datetime
import uuid

def generate_id():
    return str(uuid.uuid4())

class AgentCard(BaseModel):
    id: str
    name: str
    capabilities: List[str]
    payment_methods: List[str] = Field(default_factory=list)
    context_window_limit: int = 128000

class NegotiationSettings(BaseModel):
    aggression: int = Field(default=2, ge=0, le=5, description="How forceful the agent should be. 0 = very friendly, 5 = hard-bargainer.")
    max_rounds: int = Field(default=5, ge=1, le=10, alias="maxRounds", description="Maximum number of back-and-forth counter-offers before aborting.")
    price_margin_pct: float = Field(default=10, ge=0, le=30, alias="priceMarginPct", description="Maximum percentage below the listed price the buyer is willing to propose as the first offer.")
    response_delay_ms: int = Field(default=500, ge=0, le=5000, alias="responseDelayMs", description="Artificial delay before sending each message (simulates human typing).")
    use_llm: bool = Field(default=True, alias="useLLM", description="If false, fall back to rule-based templates only.")
    allowed_payment_methods: List[str] = Field(default_factory=lambda: ["stripe", "cash"], alias="allowedPaymentMethods", description="Payment options the buyer is willing to accept.")
    log_chat: bool = Field(default=True, alias="logChat", description="Whether to store the full chat transcript (encrypted).")

    class Config:
        populate_by_name = True

class MessagePayload(BaseModel):
    topic: Optional[str] = None
    terms: Optional[Dict[str, Any]] = None
    counter_offer: Optional[Dict[str, Any]] = None
    final_terms: Optional[Dict[str, Any]] = None
    digital_signature: Optional[str] = None
    content: Optional[str] = None # Generic content

class Message(BaseModel):
    id: str = Field(default_factory=generate_id)
    thread_id: str = Field(default_factory=generate_id)
    from_agent: str = Field(alias="from")
    to_agent: str = Field(alias="to")
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    type: Literal["PROPOSAL", "REJECTION", "ACCEPTANCE", "COMMITMENT", "INFO"]
    payload: MessagePayload
    reasoning: str

    class Config:
        populate_by_name = True
