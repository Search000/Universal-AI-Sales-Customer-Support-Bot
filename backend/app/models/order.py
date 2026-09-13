"""
Order model (Phase 7). Mirrors an ORDERS sheet tab row.

An order is only ever created from a product that KnowledgeEngine already
verified exists and is in stock for this business — order_engine never
invents a product, price, or availability.
"""
import uuid
from dataclasses import dataclass
from typing import Optional


@dataclass
class Order:
    order_id: str
    business_id: str
    customer_id: str
    product_id: str
    product_name: str
    quantity: int
    unit_price: str
    total_price: str
    currency: str
    status: str = "pending"
    created_at: str = ""

    @staticmethod
    def new_id() -> str:
        return f"ord_{uuid.uuid4().hex[:10]}"

    @staticmethod
    def from_row(row: dict) -> Optional["Order"]:
        if not row.get("order_id") or not row.get("business_id"):
            return None
        try:
            quantity = int(row.get("quantity", 1))
        except (ValueError, TypeError):
            quantity = 1
        return Order(
            order_id=str(row.get("order_id", "")),
            business_id=str(row.get("business_id", "")),
            customer_id=str(row.get("customer_id", "")),
            product_id=str(row.get("product_id", "")),
            product_name=str(row.get("product_name", "")),
            quantity=quantity,
            unit_price=str(row.get("unit_price", "")),
            total_price=str(row.get("total_price", "")),
            currency=str(row.get("currency", "")),
            status=str(row.get("status", "pending")),
            created_at=str(row.get("created_at", "")),
        )

    def to_row(self) -> dict:
        return {
            "order_id": self.order_id,
            "business_id": self.business_id,
            "customer_id": self.customer_id,
            "product_id": self.product_id,
            "product_name": self.product_name,
            "quantity": self.quantity,
            "unit_price": self.unit_price,
            "total_price": self.total_price,
            "currency": self.currency,
            "status": self.status,
            "created_at": self.created_at,
        }
