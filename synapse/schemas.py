"""
BUYER and SELLER JSON schemas for agentic negotiation system prompts
Uses camelCase fields for JSON compatibility
"""
from typing import List
from pydantic import BaseModel, Field, field_validator


class AgentConfigSchema(BaseModel):
    """Base schema for agent configuration"""
    aggression: int = Field(
        default=2,
        ge=0,
        le=5,
        description="How forceful the agent should be. 0 = very friendly, 5 = hard-bargainer."
    )
    maxRounds: int = Field(
        default=5,
        ge=1,
        le=10,
        description="Maximum number of back-and-forth counter-offers before aborting."
    )
    priceMarginPct: float = Field(
        default=10.0,
        ge=0,
        le=30,
        description="Price margin percentage (buyer: max discount, seller: min markup)."
    )
    responseDelayMs: int = Field(
        default=0,
        ge=0,
        le=5000,
        description="Artificial delay before sending each message (simulates human typing)."
    )
    useLLM: bool = Field(
        default=True,
        description="If false, fall back to rule-based templates only."
    )
    allowedPaymentMethods: List[str] = Field(
        default_factory=lambda: ["stripe", "cash"],
        description="Payment options the agent is willing to accept."
    )
    logChat: bool = Field(
        default=True,
        description="Whether to store the full chat transcript (encrypted)."
    )
    content: str = Field(
        default="",
        description="System prompt content that defines the agent's personality, goals, and negotiation style."
    )
    
    @field_validator('allowedPaymentMethods')
    @classmethod
    def validate_payment_methods(cls, v):
        valid_methods = ["stripe", "paypal", "cash"]
        return [m for m in v if m in valid_methods]


class BuyerSchema(AgentConfigSchema):
    """Schema for buyer agent configuration"""
    content: str = Field(
        default="You are a buyer negotiating for a product. Be professional, fair, and focus on getting a good deal within your budget. Always be respectful and courteous.",
        description="System prompt content that defines the buyer's personality, goals, and negotiation style."
    )


class SellerSchema(AgentConfigSchema):
    """Schema for seller agent configuration"""
    content: str = Field(
        default="You are a seller negotiating the sale of a product. Be professional, fair, and aim to get a reasonable price. Always be respectful and courteous.",
        description="System prompt content that defines the seller's personality, goals, and negotiation style."
    )


# Payment method options
PAYMENT_METHODS = ["stripe", "paypal", "cash", "venmo", "zelle", "bank_transfer"]

