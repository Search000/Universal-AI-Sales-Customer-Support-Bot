from dataclasses import dataclass
from typing import Optional


@dataclass
class Policy:
    policy_id: str
    business_id: str
    policy_type: str
    policy_text: str
    active: str = "TRUE"
    updated_at: str = ""

    @staticmethod
    def from_row(row: dict) -> Optional["Policy"]:
        if not row.get("policy_id") or not row.get("business_id") or not row.get("policy_type"):
            return None
        return Policy(
            policy_id=str(row.get("policy_id", "")).strip(),
            business_id=str(row.get("business_id", "")).strip(),
            policy_type=row.get("policy_type", ""),
            policy_text=row.get("policy_text", ""),
            active=row.get("active", "TRUE"),
            updated_at=row.get("updated_at", ""),
        )
