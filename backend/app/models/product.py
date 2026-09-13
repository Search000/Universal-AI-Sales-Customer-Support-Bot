from dataclasses import dataclass
from typing import Optional


@dataclass
class Product:
    product_id: str
    business_id: str
    product_name: str
    description: str = ""
    category: str = ""
    price: str = ""
    currency: str = ""
    stock: str = ""
    stock_status: str = ""
    size: str = ""
    color: str = ""
    variant: str = ""
    sku: str = ""
    image_url: str = ""
    delivery_available: str = ""
    active: str = "TRUE"
    updated_at: str = ""

    @staticmethod
    def from_row(row: dict) -> Optional["Product"]:
        if not row.get("product_id") or not row.get("business_id") or not row.get("product_name"):
            return None
        return Product(
            product_id=str(row.get("product_id", "")).strip(),
            business_id=str(row.get("business_id", "")).strip(),
            product_name=row.get("product_name", ""),
            description=row.get("description", ""),
            category=row.get("category", ""),
            price=row.get("price", ""),
            currency=row.get("currency", ""),
            stock=row.get("stock", ""),
            stock_status=row.get("stock_status", ""),
            size=row.get("size", ""),
            color=row.get("color", ""),
            variant=row.get("variant", ""),
            sku=row.get("sku", ""),
            image_url=row.get("image_url", ""),
            delivery_available=row.get("delivery_available", ""),
            active=row.get("active", "TRUE"),
            updated_at=row.get("updated_at", ""),
        )
