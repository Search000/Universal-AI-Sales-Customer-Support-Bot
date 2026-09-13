"""
Conversation Memory model (Phase 6).

Mirrors a CONVERSATIONS sheet tab: one row per (business_id, customer_id)
pair, storing the last known entities/intent so a customer's context
survives an app restart (unlike the old in-memory-only dict from Phase 4).
"""
from dataclasses import dataclass
from typing import Optional


@dataclass
class ConversationMemory:
    business_id: str
    customer_id: str
    last_intent: str = ""
    last_color: str = ""
    last_size: str = ""
    last_keywords: str = ""  # comma-separated
    updated_at: str = ""

    @staticmethod
    def from_row(row: dict) -> Optional["ConversationMemory"]:
        if not row.get("business_id") or not row.get("customer_id"):
            return None
        return ConversationMemory(
            business_id=str(row.get("business_id", "")),
            customer_id=str(row.get("customer_id", "")),
            last_intent=str(row.get("last_intent", "")),
            last_color=str(row.get("last_color", "")),
            last_size=str(row.get("last_size", "")),
            last_keywords=str(row.get("last_keywords", "")),
            updated_at=str(row.get("updated_at", "")),
        )

    def to_row(self) -> dict:
        return {
            "business_id": self.business_id,
            "customer_id": self.customer_id,
            "last_intent": self.last_intent,
            "last_color": self.last_color,
            "last_size": self.last_size,
            "last_keywords": self.last_keywords,
            "updated_at": self.updated_at,
        }
