"""
Order Engine (Phase 7).

Creates an order ONLY from a product the KnowledgeEngine has already
verified exists and is in stock for this exact business_id. This engine
never invents a product, price, or stock status — if the product can't be
verified, order creation is refused with a clear reason instead of
guessing (master rules #2 and #3, same discipline as every other engine).
"""
import logging
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Optional

from app.integrations.sheets.repository import SheetsRepository
from app.models.order import Order
from app.services.knowledge_engine import KnowledgeEngine

logger = logging.getLogger(__name__)


class OrderError(ValueError):
    """Raised when an order cannot be created — always with a safe,
    customer-facing reason (product not found, out of stock, etc.)."""


@dataclass
class OrderResult:
    order: Optional[Order]
    error: Optional[str] = None


class OrderEngine:
    def __init__(self, knowledge_engine: KnowledgeEngine, repository: SheetsRepository):
        self._engine = knowledge_engine
        self._repo = repository

    def place_order(
        self,
        business_id: str,
        customer_id: str,
        product_id: str,
        quantity: int = 1,
    ) -> OrderResult:
        if quantity < 1:
            return OrderResult(order=None, error="quantity must be at least 1")

        # Re-verify against this business's real data — never trust a
        # product_id blindly, even if it came from an earlier pipeline step.
        products = self._engine.find_products(business_id)
        product = next((p for p in products if p.product_id == product_id), None)
        if product is None:
            return OrderResult(order=None, error="PRODUCT_NOT_FOUND")

        stock = self._engine.get_stock(business_id, product_id)
        if stock is None or not stock.in_stock:
            return OrderResult(order=None, error="OUT_OF_STOCK")
        if stock.stock_count is not None and stock.stock_count < quantity:
            return OrderResult(order=None, error="INSUFFICIENT_STOCK")

        try:
            unit_price = float(product.price)
            total_price = unit_price * quantity
        except (ValueError, TypeError):
            unit_price = product.price
            total_price = ""

        order = Order(
            order_id=Order.new_id(),
            business_id=business_id,
            customer_id=customer_id or "anonymous",
            product_id=product.product_id,
            product_name=product.product_name,
            quantity=quantity,
            unit_price=str(unit_price),
            total_price=str(total_price),
            currency=product.currency,
            status="pending",
            created_at=datetime.now(timezone.utc).isoformat(),
        )
        self._repo.create_order(order)
        return OrderResult(order=order, error=None)

    def list_customer_orders(self, business_id: str, customer_id: str):
        return self._repo.list_orders(business_id, customer_id)
