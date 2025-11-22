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
