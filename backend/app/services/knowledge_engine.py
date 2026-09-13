"""
Business Knowledge Engine (Phase 3).

Wraps SheetsRepository with the actual retrieval logic the AI pipeline will
call: product/service/FAQ/policy/business-rule/vocabulary lookups, plus
stock and price checks. Every method requires business_id and only returns
that business's data — isolation is enforced one layer below (repository)
and re-verified here with belt-and-braces checks.

This engine does NOT talk to any AI model. It only returns verified facts
or None. Deciding what to say when facts are missing is the response
engine's job (Phase 5).
"""
import logging
from dataclasses import dataclass
from typing import List, Optional

from app.integrations.sheets.repository import SheetsRepository
from app.models.product import Product
from app.models.service import Service
from app.models.faq import FAQ
from app.models.policy import Policy
from app.models.business_rule import BusinessRule
from app.models.vocabulary import Vocabulary

logger = logging.getLogger(__name__)


@dataclass
class StockInfo:
    product_id: str
    in_stock: bool
    stock_count: Optional[int]
    stock_status: str


class KnowledgeEngine:
    def __init__(self, repository: SheetsRepository):
        self._repo = repository

    # ---- internal safety check -------------------------------------------
    @staticmethod
    def _assert_owned(business_id: str, items: list, id_field: str = "business_id"):
        """Defence in depth: even though repository already filters by
        business_id, refuse to return anything that doesn't match."""
        for item in items:
            owner = getattr(item, id_field, None)
            if owner != business_id:
                raise RuntimeError(
                    f"Isolation breach detected: item owned by '{owner}' "
                    f"returned for business '{business_id}'"
                )
        return items

    # ---- PRODUCTS ------------------------------------------------------
    def find_products(
        self,
        business_id: str,
        name_contains: Optional[str] = None,
        color: Optional[str] = None,
        size: Optional[str] = None,
    ) -> List[Product]:
        results = self._repo.find_products(business_id, name_contains, color, size)
        return self._assert_owned(business_id, results)

    def get_stock(self, business_id: str, product_id: str) -> Optional[StockInfo]:
        for product in self._repo.list_products(business_id):
            if product.product_id == product_id:
                try:
                    count = int(product.stock)
                except (ValueError, TypeError):
                    count = None
                in_stock = (count is not None and count > 0) or (
                    product.stock_status.lower() == "in_stock"
                )
                return StockInfo(
                    product_id=product_id,
                    in_stock=in_stock,
                    stock_count=count,
                    stock_status=product.stock_status,
                )
        return None  # unknown product for this business — do not guess

    def get_price(self, business_id: str, product_id: str) -> Optional[str]:
        for product in self._repo.list_products(business_id):
            if product.product_id == product_id:
                return product.price
        return None

    # ---- SERVICES ------------------------------------------------------
    def find_services(self, business_id: str, name_contains: Optional[str] = None) -> List[Service]:
        services = self._repo.list_services(business_id)
        if name_contains:
            services = [s for s in services if name_contains.lower() in s.service_name.lower()]
        return self._assert_owned(business_id, services)

    # ---- FAQ / POLICY / RULES ------------------------------------------
    def search_faq(self, business_id: str, keyword: str) -> List[FAQ]:
        faqs = self._repo.list_faqs(business_id)
        keyword = keyword.lower()
        matches = [
            f for f in faqs
            if keyword in f.question.lower() or keyword in f.keywords.lower()
        ]
        return self._assert_owned(business_id, matches)

    def get_policy(self, business_id: str, policy_type: str) -> Optional[Policy]:
        policy = self._repo.get_policy(business_id, policy_type)
        if policy:
            self._assert_owned(business_id, [policy])
        return policy

    def get_business_rule(self, business_id: str, rule_name: str) -> Optional[BusinessRule]:
        rule = self._repo.get_business_rule(business_id, rule_name)
        if rule:
            self._assert_owned(business_id, [rule])
        return rule

    # ---- VOCABULARY ------------------------------------------------------
    def resolve_vocabulary(self, business_id: str, term: str) -> Optional[Vocabulary]:
        vocab = self._repo.resolve_vocabulary_term(business_id, term)
        if vocab:
            self._assert_owned(business_id, [vocab])
        return vocab
