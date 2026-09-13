import uuid
from dataclasses import dataclass
from typing import Optional


@dataclass
class Vocabulary:
    vocab_id: str
    business_id: str
    term: str
    meaning: str
    category: str = ""
    examples: str = ""
    approved: str = "FALSE"
    updated_at: str = ""

    @staticmethod
    def new_id() -> str:
        return f"vocab_{uuid.uuid4().hex[:10]}"

    @staticmethod
    def from_row(row: dict) -> Optional["Vocabulary"]:
        if not row.get("vocab_id") or not row.get("business_id") or not row.get("term"):
            return None
        return Vocabulary(
            vocab_id=str(row.get("vocab_id", "")).strip(),
            business_id=str(row.get("business_id", "")).strip(),
            term=row.get("term", ""),
            meaning=row.get("meaning", ""),
            category=row.get("category", ""),
            examples=row.get("examples", ""),
            approved=row.get("approved", "FALSE"),
            updated_at=row.get("updated_at", ""),
        )

    def to_row(self) -> dict:
        return {
            "vocab_id": self.vocab_id,
            "business_id": self.business_id,
            "term": self.term,
            "meaning": self.meaning,
            "category": self.category,
            "examples": self.examples,
            "approved": self.approved,
            "updated_at": self.updated_at,
        }
