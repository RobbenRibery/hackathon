"""
Helper functions to load and use BUYER/SELLER schemas as system prompts
"""
import json
from pathlib import Path
from typing import Optional
from .schemas import BuyerSchema, SellerSchema


def load_buyer_config(config_path: Optional[Path] = None) -> BuyerSchema:
    """Load buyer configuration from JSON file."""
    if config_path is None:
        config_path = Path("config/buyer.json")
    
    if config_path.exists():
        with open(config_path, 'r') as f:
            data = json.load(f)
        return BuyerSchema(**data)
    return BuyerSchema()


def load_seller_config(config_path: Optional[Path] = None) -> SellerSchema:
    """Load seller configuration from JSON file."""
    if config_path is None:
        config_path = Path("config/seller.json")
    
    if config_path.exists():
        with open(config_path, 'r') as f:
            data = json.load(f)
        return SellerSchema(**data)
    return SellerSchema()


def build_system_prompt_from_schema(schema, agent_type: str = "buyer") -> str:
    """
    Build a comprehensive system prompt from a schema.
    
    Args:
        schema: BuyerSchema or SellerSchema instance
        agent_type: "buyer" or "seller"
    
    Returns:
        Formatted system prompt string
    """
    role = "buyer" if agent_type.lower() == "buyer" else "seller"
    
    # Aggression level descriptions
    aggression_levels = {
        0: "very friendly and collaborative",
        1: "friendly and warm",
        2: "professional and balanced",
        3: "assertive and firm",
        4: "aggressive and data-driven",
        5: "hard-bargaining and willing to walk away"
    }
    
    aggression_desc = aggression_levels.get(schema.aggression, "professional")
    
    # Use camelCase field names
    prompt_parts = [
        schema.content,
        "",
        f"Your negotiation style: {aggression_desc} (aggression level {schema.aggression}/5)",
        f"Maximum negotiation rounds: {schema.maxRounds}",
        f"Price margin: {schema.priceMarginPct}%",
        f"Allowed payment methods: {', '.join(schema.allowedPaymentMethods)}",
        f"Use LLM: {schema.useLLM}",
        f"Response delay: {schema.responseDelayMs}ms",
        "",
        "Remember to:",
        "- Stay within your defined negotiation parameters",
        "- Be respectful and professional",
        "- Make clear, actionable proposals",
        "- Respond appropriately based on your aggression level"
    ]
    
    return "\n".join(prompt_parts)

