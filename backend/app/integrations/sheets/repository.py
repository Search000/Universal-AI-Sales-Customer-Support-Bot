"""
Repository layer: the ONLY place services are allowed to read business data
from. Every lookup here REQUIRES business_id and filters on it — this is
where business isolation (master rule #4) is enforced in code, not just
by convention.
"""
import logging
from typing import List, Optional

from app.integrations.sheets.client import SheetClient
from app.models.business import Business
from app.models.product import Product
from app.models.service import Service
from app.models.faq import FAQ
from app.models.policy import Policy

logger = logging.getLogger(__name__)


class BusinessIdRequiredError(ValueError):
    """Raised when a lookup is attempted without a business_id."""


class SheetsRepository:
    def __init__(self, client: SheetClient):
        self._client = client

    # ---- internal helper -------------------------------------------------
    def _require_business_id(self, business_id: Optional[str]) -> str:
        if not business_id or not str(business_id).strip():
            raise BusinessIdRequiredError(
                "business_id is required for any data lookup — refusing to "
                "query without it to prevent cross-business leakage."
            )
        return str(business_id).strip()

    # ---- BUSINESSES --------------------------------------------------------
    def get_business(self, business_id: str) -> Optional[Business]:
        business_id = self._require_business_id(business_id)
        rows = self._client.get_all_records("BUSINESSES")
        for row in rows:
            biz = Business.from_row(row)
            if biz and biz.business_id == business_id:
                return biz
        return None

    # ---- PRODUCTS ------------------------------------------------------
    def list_products(self, business_id: str) -> List[Product]:
        business_id = self._require_business_id(business_id)
        rows = self._client.get_all_records("PRODUCTS")
        results = []
        for row in rows:
            product = Product.from_row(row)
            if product and product.business_id == business_id:
                results.append(product)
        return results

    def find_products(
        self,
        business_id: str,
        name_contains: Optional[str] = None,
        color: Optional[str] = None,
        size: Optional[str] = None,
    ) -> List[Product]:
        products = self.list_products(business_id)
        results = []
        for p in products:
            if name_contains and name_contains.lower() not in p.product_name.lower():
                continue
            if color and color.lower() != p.color.lower():
                continue
            if size and size.lower() != p.size.lower():
                continue
            results.append(p)
        return results

    # ---- SERVICES ------------------------------------------------------
    def list_services(self, business_id: str) -> List[Service]:
        business_id = self._require_business_id(business_id)
        rows = self._client.get_all_records("SERVICES")
        results = []
        for row in rows:
            service = Service.from_row(row)
            if service and service.business_id == business_id:
                results.append(service)
        return results

    # ---- FAQ -------------------------------------------------------------
    def list_faqs(self, business_id: str) -> List[FAQ]:
        business_id = self._require_business_id(business_id)
        rows = self._client.get_all_records("FAQ")
        results = []
        for row in rows:
            faq = FAQ.from_row(row)
            if faq and faq.business_id == business_id:
                results.append(faq)
        return results

    # ---- POLICIES ------------------------------------------------------
    def list_policies(self, business_id: str) -> List[Policy]:
        business_id = self._require_business_id(business_id)
        rows = self._client.get_all_records("POLICIES")
        results = []
        for row in rows:
            policy = Policy.from_row(row)
            if policy and policy.business_id == business_id:
                results.append(policy)
        return results

    def get_policy(self, business_id: str, policy_type: str) -> Optional[Policy]:
        for policy in self.list_policies(business_id):
            if policy.policy_type.lower() == policy_type.lower():
                return policy
        return None
