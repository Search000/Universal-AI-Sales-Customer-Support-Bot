"""
Typed row models mirroring Google Sheets tabs.
Each model has from_row() to build from a raw dict (sheet row) and
validates that required fields are present — bad rows are skipped, not guessed.
"""
from dataclasses import dataclass
from typing import Optional


@dataclass
class Business:
    business_id: str
    business_name: str
    business_type: str
    facebook_page_id: str = ""
    whatsapp_phone_number_id: str = ""
    phone: str = ""
    email: str = ""
    address: str = ""
    opening_hours: str = ""
    currency: str = ""
    default_language: str = ""
    status: str = "active"
    created_at: str = ""

    @staticmethod
    def from_row(row: dict) -> Optional["Business"]:
        if not row.get("business_id") or not row.get("business_name"):
            return None
        return Business(
            business_id=str(row.get("business_id", "")).strip(),
            business_name=row.get("business_name", ""),
            business_type=row.get("business_type", ""),
            facebook_page_id=row.get("facebook_page_id", ""),
            whatsapp_phone_number_id=row.get("whatsapp_phone_number_id", ""),
            phone=row.get("phone", ""),
            email=row.get("email", ""),
            address=row.get("address", ""),
            opening_hours=row.get("opening_hours", ""),
            currency=row.get("currency", ""),
            default_language=row.get("default_language", ""),
            status=row.get("status", "active"),
            created_at=row.get("created_at", ""),
        )
