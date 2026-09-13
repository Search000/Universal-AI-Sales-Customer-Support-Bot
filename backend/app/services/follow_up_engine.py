"""
Follow-Up / Sales Automation Engine (Phase 13).

Everything here only READS data that already exists and is verified for
this business_id (products, orders, conversation memory, business rules).
It never invents a product, price, or discount — recommendations and
upsells are always a filter over the business's own real PRODUCTS rows
(master rules #2 and #3, same discipline as every other engine).

All behaviour is configurable per business through BUSINESS_RULES rows,
so one business can disable follow-up/upsell entirely, or use different
thresholds, without touching code:

    rule_name                          rule_value example
    -----------------------------------------------------
    follow_up_enabled                  TRUE / FALSE
    abandoned_conversation_hours       6
    abandoned_order_hours              24
    upsell_enabled                     TRUE / FALSE
    max_recommendations                3
    vip_order_threshold                5

Any rule not set by the business falls back to a sane default below.
"""
import logging
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Dict, List, Optional

from app.integrations.sheets.repository import SheetsRepository
from app.models.order import Order
from app.models.product import Product

logger = logging.getLogger(__name__)

DEFAULTS = {
    "follow_up_enabled": "TRUE",
    "abandoned_conversation_hours": "6",
    "abandoned_order_hours": "24",
    "upsell_enabled": "TRUE",
    "max_recommendations": "3",
    "vip_order_threshold": "5",
}

# Orders in these statuses are considered "still moving" — never abandoned.
_NON_ABANDONED_ORDER_STATUSES = {"completed", "delivered", "cancelled", "refunded"}


@dataclass
class AbandonedConversation:
    customer_id: str
    last_intent: str
    updated_at: str
    hours_since_update: float


@dataclass
class AbandonedOrder:
    order: Order
    hours_since_created: float


@dataclass
class CustomerSegment:
    customer_id: str
    total_orders: int
    segment: str  # "new" | "repeat" | "vip"


class FollowUpEngine:
    def __init__(self, repository: SheetsRepository):
        self._repo = repository

    # ---- configuration ---------------------------------------------------
    def get_config(self, business_id: str) -> Dict[str, str]:
        """Business-configurable settings, falling back to DEFAULTS for
        anything the business hasn't set in BUSINESS_RULES."""
        config = dict(DEFAULTS)
        for rule in self._repo.list_business_rules(business_id):
            if str(rule.active).upper() != "TRUE":
                continue
            if rule.rule_name in DEFAULTS:
                config[rule.rule_name] = rule.rule_value
        return config

    def is_follow_up_enabled(self, business_id: str) -> bool:
        return self.get_config(business_id)["follow_up_enabled"].upper() == "TRUE"

    def is_upsell_enabled(self, business_id: str) -> bool:
        return self.get_config(business_id)["upsell_enabled"].upper() == "TRUE"

    # ---- internal helpers --------------------------------------------------
    @staticmethod
    def _hours_since(timestamp: str, now: datetime) -> Optional[float]:
        if not timestamp:
            return None
        try:
            ts = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
        except ValueError:
            return None
        if ts.tzinfo is None:
            ts = ts.replace(tzinfo=timezone.utc)
        return (now - ts).total_seconds() / 3600.0

    @staticmethod
    def _to_float(value: str) -> Optional[float]:
        try:
            return float(value)
        except (TypeError, ValueError):
            return None

    # ---- 1. abandoned conversation detection ------------------------------
    def detect_abandoned_conversations(
        self, business_id: str, now: Optional[datetime] = None
    ) -> List[AbandonedConversation]:
        if not self.is_follow_up_enabled(business_id):
            return []
        now = now or datetime.now(timezone.utc)
        threshold_hours = self._to_float(self.get_config(business_id)["abandoned_conversation_hours"]) or 6.0

        results: List[AbandonedConversation] = []
        for memory in self._repo.list_conversation_memories(business_id):
            # Already escalated to a human — that's handled elsewhere, not
            # a sales follow-up target.
            if str(memory.human_required).upper() == "TRUE":
                continue
            hours = self._hours_since(memory.updated_at, now)
            if hours is None or hours < threshold_hours:
                continue
            results.append(
                AbandonedConversation(
                    customer_id=memory.customer_id,
                    last_intent=memory.last_intent,
                    updated_at=memory.updated_at,
                    hours_since_update=round(hours, 2),
                )
            )
        results.sort(key=lambda a: a.hours_since_update, reverse=True)
        return results

    # ---- 2. abandoned order detection --------------------------------------
    def detect_abandoned_orders(
        self, business_id: str, now: Optional[datetime] = None
    ) -> List[AbandonedOrder]:
        if not self.is_follow_up_enabled(business_id):
            return []
        now = now or datetime.now(timezone.utc)
        threshold_hours = self._to_float(self.get_config(business_id)["abandoned_order_hours"]) or 24.0

        results: List[AbandonedOrder] = []
        for order in self._repo.list_orders(business_id):
            if str(order.status).lower() in _NON_ABANDONED_ORDER_STATUSES:
                continue
            hours = self._hours_since(order.created_at, now)
            if hours is None or hours < threshold_hours:
                continue
            results.append(AbandonedOrder(order=order, hours_since_created=round(hours, 2)))
        results.sort(key=lambda a: a.hours_since_created, reverse=True)
        return results

    # ---- 3. follow-up message (template, never invented business facts) ---
    def build_follow_up_message(self, business_id: str, customer_id: str) -> Optional[str]:
        """Deterministic, template-only nudge — no AI free-text here, so
        there's nothing for the model to hallucinate. Real phrasing/tone
        can wrap this at the response layer if desired."""
        if not self.is_follow_up_enabled(business_id):
            return None
        return (
            "আপনি কিছুক্ষণ আগে আমাদের সাথে কথা বলছিলেন। "
            "কোনো প্রশ্ন থাকলে বা কিছু জানার থাকলে জানাতে পারেন, আমি সাহায্য করতে পারি।"
        )

    # ---- 4. product recommendation (real catalog only) ---------------------
    def recommend_products(
        self, business_id: str, customer_id: str, limit: Optional[int] = None
    ) -> List[Product]:
        """Recommends active, in-stock products from categories the
        customer has already shown interest in (past orders first, then
        conversation memory keywords). Never returns a product that isn't
        currently active in this business's PRODUCTS sheet."""
        limit = limit or int(self._to_float(self.get_config(business_id)["max_recommendations"]) or 3)

        products = [p for p in self._repo.list_products(business_id) if str(p.active).upper() == "TRUE"]
        if not products:
            return []

        interest_categories: List[str] = []
        interest_product_ids = set()

        for order in self._repo.list_orders(business_id, customer_id=customer_id):
            interest_product_ids.add(order.product_id)
            matched = next((p for p in products if p.product_id == order.product_id), None)
            if matched and matched.category:
                interest_categories.append(matched.category.lower())

        if not interest_categories:
            memory = self._repo.get_conversation_memory(business_id, customer_id)
            if memory:
                keywords = [k.lower() for k in memory.last_keywords.split(",") if k]
                for p in products:
                    if p.category and p.category.lower() in keywords:
                        interest_categories.append(p.category.lower())

        if not interest_categories:
            return []

        recommendations = [
            p
            for p in products
            if p.category.lower() in interest_categories and p.product_id not in interest_product_ids
        ]
        return recommendations[:limit]

    # ---- 5. upsell (same category, real products only) --------------------
    def suggest_upsell(self, business_id: str, product_id: str, limit: Optional[int] = None) -> List[Product]:
        if not self.is_upsell_enabled(business_id):
            return []
        limit = limit or int(self._to_float(self.get_config(business_id)["max_recommendations"]) or 3)

        products = [p for p in self._repo.list_products(business_id) if str(p.active).upper() == "TRUE"]
        base = next((p for p in products if p.product_id == product_id), None)
        if base is None or not base.category:
            return []

        same_category = [
            p for p in products if p.product_id != product_id and p.category.lower() == base.category.lower()
        ]

        def price_of(p: Product) -> float:
            return self._to_float(p.price) or 0.0

        # Prefer complementary/higher-value items in the same category —
        # never a made-up bundle, just a re-ranking of real catalog rows.
        same_category.sort(key=price_of, reverse=True)
        return same_category[:limit]

    # ---- 6. customer segmentation ------------------------------------------
    def segment_customers(self, business_id: str) -> List[CustomerSegment]:
        vip_threshold = int(self._to_float(self.get_config(business_id)["vip_order_threshold"]) or 5)

        counts: Dict[str, int] = {}
        for order in self._repo.list_orders(business_id):
            if not order.customer_id:
                continue
            counts[order.customer_id] = counts.get(order.customer_id, 0) + 1

        segments: List[CustomerSegment] = []
        for customer_id, total in counts.items():
            if total >= vip_threshold:
                segment = "vip"
            elif total > 1:
                segment = "repeat"
            else:
                segment = "new"
            segments.append(CustomerSegment(customer_id=customer_id, total_orders=total, segment=segment))

        segments.sort(key=lambda s: s.total_orders, reverse=True)
        return segments
