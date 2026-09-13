from dataclasses import dataclass
from typing import Optional


@dataclass
class BusinessRule:
    rule_id: str
    business_id: str
    rule_name: str
    rule_value: str
    priority: str = ""
    active: str = "TRUE"
    updated_at: str = ""

    @staticmethod
    def from_row(row: dict) -> Optional["BusinessRule"]:
        if not row.get("rule_id") or not row.get("business_id") or not row.get("rule_name"):
            return None
        return BusinessRule(
            rule_id=str(row.get("rule_id", "")).strip(),
            business_id=str(row.get("business_id", "")).strip(),
            rule_name=row.get("rule_name", ""),
            rule_value=row.get("rule_value", ""),
            priority=row.get("priority", ""),
            active=row.get("active", "TRUE"),
            updated_at=row.get("updated_at", ""),
        )
