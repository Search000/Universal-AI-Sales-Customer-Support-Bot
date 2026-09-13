"""
Learning Queue model (Phase 8).

Master rule #7: customer messages are NEVER auto-trusted as business facts.
An unknown term detected in a customer message lands here as
UNKNOWN_TERM / POSSIBLE_PRODUCT with status=pending. It only becomes real,
usable business vocabulary after a human owner explicitly approves it
(learning_engine.approve -> writes a VOCABULARY row).
"""
import uuid
from dataclasses import dataclass
from typing import Optional


@dataclass
class LearningQueueEntry:
    learning_id: str
    business_id: str
    term: str
    possible_meaning: str = ""
    context: str = ""
    confidence: str = "0.5"
    source: str = "customer_message"
    status: str = "pending"  # pending | approved | rejected | ignored
    created_at: str = ""
    approved_by: str = ""
    approved_at: str = ""
    reviewed_at: str = ""

    @staticmethod
    def new_id() -> str:
        return f"lrn_{uuid.uuid4().hex[:10]}"

    @staticmethod
    def from_row(row: dict) -> Optional["LearningQueueEntry"]:
        if not row.get("learning_id") or not row.get("business_id") or not row.get("term"):
            return None
        return LearningQueueEntry(
            learning_id=str(row.get("learning_id", "")).strip(),
            business_id=str(row.get("business_id", "")).strip(),
            term=str(row.get("term", "")),
            possible_meaning=str(row.get("possible_meaning", "")),
            context=str(row.get("context", "")),
            confidence=str(row.get("confidence", "0.5")),
            source=str(row.get("source", "customer_message")),
            status=str(row.get("status", "pending")),
            created_at=str(row.get("created_at", "")),
            approved_by=str(row.get("approved_by", "")),
            approved_at=str(row.get("approved_at", "")),
            reviewed_at=str(row.get("reviewed_at", "")),
        )

    def to_row(self) -> dict:
        return {
            "learning_id": self.learning_id,
            "business_id": self.business_id,
            "term": self.term,
            "possible_meaning": self.possible_meaning,
            "context": self.context,
            "confidence": self.confidence,
            "source": self.source,
            "status": self.status,
            "created_at": self.created_at,
            "approved_by": self.approved_by,
            "approved_at": self.approved_at,
            "reviewed_at": self.reviewed_at,
        }
