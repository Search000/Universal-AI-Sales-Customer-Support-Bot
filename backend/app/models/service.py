from dataclasses import dataclass
from typing import Optional


@dataclass
class Service:
    service_id: str
    business_id: str
    service_name: str
    description: str = ""
    price: str = ""
    duration: str = ""
    availability: str = ""
    active: str = "TRUE"
    updated_at: str = ""

    @staticmethod
    def from_row(row: dict) -> Optional["Service"]:
        if not row.get("service_id") or not row.get("business_id") or not row.get("service_name"):
            return None
        return Service(
            service_id=str(row.get("service_id", "")).strip(),
            business_id=str(row.get("business_id", "")).strip(),
            service_name=row.get("service_name", ""),
            description=row.get("description", ""),
            price=row.get("price", ""),
            duration=row.get("duration", ""),
            availability=row.get("availability", ""),
            active=row.get("active", "TRUE"),
            updated_at=row.get("updated_at", ""),
        )
