from dataclasses import dataclass
from typing import Optional


@dataclass
class FAQ:
    faq_id: str
    business_id: str
    question: str
    answer: str
    keywords: str = ""
    active: str = "TRUE"
    updated_at: str = ""

    @staticmethod
    def from_row(row: dict) -> Optional["FAQ"]:
        if not row.get("faq_id") or not row.get("business_id") or not row.get("question"):
            return None
        return FAQ(
            faq_id=str(row.get("faq_id", "")).strip(),
            business_id=str(row.get("business_id", "")).strip(),
            question=row.get("question", ""),
            answer=row.get("answer", ""),
            keywords=row.get("keywords", ""),
            active=row.get("active", "TRUE"),
            updated_at=row.get("updated_at", ""),
        )
