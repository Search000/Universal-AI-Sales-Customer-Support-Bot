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
from app.models.business_rule import BusinessRule
from app.models.vocabulary import Vocabulary
from app.models.conversation_memory import ConversationMemory
from app.models.order import Order
from app.models.learning_queue import LearningQueueEntry

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

    def update_business(self, business: Business) -> None:
        """Save changes to an existing business's own settings row (name,
        contact info, hours, channel IDs, etc). Never used to create a new
        business or to touch another business's row — caller must always
        load the existing Business first via get_business()."""
        self._require_business_id(business.business_id)
        self._client.upsert_row(
            "BUSINESSES",
            key_fields={"business_id": business.business_id},
            row=business.__dict__,
        )

    def create_business(self, business: Business) -> None:
        """Onboard a brand-new client. Refuses to run if a business with
        this business_id already exists — creation and update are kept as
        separate, explicit operations so one can never silently do the
        other's job."""
        self._require_business_id(business.business_id)
        if self.get_business(business.business_id) is not None:
            raise ValueError(f"business_id '{business.business_id}' already exists")
        self._client.upsert_row(
            "BUSINESSES",
            key_fields={"business_id": business.business_id},
            row=business.__dict__,
        )

    def get_business_by_facebook_page_id(self, page_id: str) -> Optional[Business]:
        """Identify WHICH business a Messenger webhook event belongs to.

        This is the one lookup allowed to run before a business_id is known —
        that's the whole point (Messenger tells us the Page ID, not the
        business_id). It still never returns data from more than one
        business: it stops at the first exact page-id match.
        """
        page_id = str(page_id or "").strip()
        if not page_id:
            return None
        rows = self._client.get_all_records("BUSINESSES")
        for row in rows:
            biz = Business.from_row(row)
            if biz and str(biz.facebook_page_id or "").strip() == page_id:
                return biz
        return None

    def get_business_by_whatsapp_phone_number_id(self, phone_number_id: str) -> Optional[Business]:
        """Identify WHICH business a WhatsApp webhook event belongs to,
        mirroring get_business_by_facebook_page_id above — same reasoning,
        different channel identifier."""
        phone_number_id = str(phone_number_id or "").strip()
        if not phone_number_id:
            return None
        rows = self._client.get_all_records("BUSINESSES")
        for row in rows:
            biz = Business.from_row(row)
            if biz and str(biz.whatsapp_phone_number_id or "").strip() == phone_number_id:
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

    # ---- BUSINESS_RULES ----------------------------------------------
    def list_business_rules(self, business_id: str) -> List[BusinessRule]:
        business_id = self._require_business_id(business_id)
        rows = self._client.get_all_records("BUSINESS_RULES")
        results = []
        for row in rows:
            rule = BusinessRule.from_row(row)
            if rule and rule.business_id == business_id:
                results.append(rule)
        return results

    def get_business_rule(self, business_id: str, rule_name: str) -> Optional[BusinessRule]:
        for rule in self.list_business_rules(business_id):
            if rule.rule_name.lower() == rule_name.lower():
                return rule
        return None

    # ---- VOCABULARY (business-specific only, never shared) -----------
    def list_vocabulary(self, business_id: str, approved_only: bool = True) -> List[Vocabulary]:
        business_id = self._require_business_id(business_id)
        rows = self._client.get_all_records("VOCABULARY")
        results = []
        for row in rows:
            vocab = Vocabulary.from_row(row)
            if not vocab or vocab.business_id != business_id:
                continue
            if approved_only and str(vocab.approved).upper() != "TRUE":
                continue
            results.append(vocab)
        return results

    def resolve_vocabulary_term(self, business_id: str, term: str) -> Optional[Vocabulary]:
        """Look up ONLY this business's approved vocabulary for a term.
        Never falls back to another business's meaning for the same word."""
        for vocab in self.list_vocabulary(business_id, approved_only=True):
            if vocab.term.lower() == term.lower():
                return vocab
        return None

    def save_vocabulary(self, vocab: Vocabulary) -> None:
        """Write an owner-approved vocabulary row. Called only from the
        learning engine's approve() path — never directly from customer
        input (master rule #7)."""
        self._require_business_id(vocab.business_id)
        self._client.upsert_row(
            "VOCABULARY",
            key_fields={"vocab_id": vocab.vocab_id},
            row=vocab.to_row(),
        )

    # ---- LEARNING_QUEUE (Phase 8) -----------------------------------------
    def create_learning_entry(self, entry: LearningQueueEntry) -> None:
        self._require_business_id(entry.business_id)
        self._client.upsert_row(
            "LEARNING_QUEUE",
            key_fields={"learning_id": entry.learning_id},
            row=entry.to_row(),
        )

    def list_learning_queue(
        self, business_id: str, status: Optional[str] = None
    ) -> List[LearningQueueEntry]:
        business_id = self._require_business_id(business_id)
        rows = self._client.get_all_records("LEARNING_QUEUE")
        results = []
        for row in rows:
            entry = LearningQueueEntry.from_row(row)
            if not entry or entry.business_id != business_id:
                continue
            if status and entry.status != status:
                continue
            results.append(entry)
        return results

    def get_learning_entry(self, business_id: str, learning_id: str) -> Optional[LearningQueueEntry]:
        for entry in self.list_learning_queue(business_id):
            if entry.learning_id == learning_id:
                return entry
        return None

    def update_learning_entry(self, entry: LearningQueueEntry) -> None:
        self._require_business_id(entry.business_id)
        self._client.upsert_row(
            "LEARNING_QUEUE",
            key_fields={"learning_id": entry.learning_id},
            row=entry.to_row(),
        )

    # ---- CONVERSATION_MEMORY (Phase 6) ---------------------------------
    def get_conversation_memory(
        self, business_id: str, customer_id: str
    ) -> Optional[ConversationMemory]:
        business_id = self._require_business_id(business_id)
        rows = self._client.get_all_records("CONVERSATIONS")
        for row in rows:
            memory = ConversationMemory.from_row(row)
            if memory and memory.business_id == business_id and memory.customer_id == customer_id:
                return memory
        return None

    def list_conversation_memories(self, business_id: str) -> List[ConversationMemory]:
        """All known conversation states for a business — the data source
        for the owner dashboard's Conversations view. Business-scoped like
        every other lookup here."""
        business_id = self._require_business_id(business_id)
        rows = self._client.get_all_records("CONVERSATIONS")
        results = []
        for row in rows:
            memory = ConversationMemory.from_row(row)
            if memory and memory.business_id == business_id:
                results.append(memory)
        return results

    def save_conversation_memory(self, memory: ConversationMemory) -> None:
        self._require_business_id(memory.business_id)
        self._client.upsert_row(
            "CONVERSATIONS",
            key_fields={"business_id": memory.business_id, "customer_id": memory.customer_id},
            row=memory.to_row(),
        )

    # ---- ORDERS (Phase 7) ------------------------------------------------
    def create_order(self, order: Order) -> None:
        self._require_business_id(order.business_id)
        # key on order_id: a fresh order_id never matches an existing row,
        # so this always appends rather than overwriting another order.
        self._client.upsert_row(
            "ORDERS",
            key_fields={"order_id": order.order_id},
            row=order.to_row(),
        )

    def list_orders(self, business_id: str, customer_id: Optional[str] = None) -> List[Order]:
        business_id = self._require_business_id(business_id)
        rows = self._client.get_all_records("ORDERS")
        results = []
        for row in rows:
            order = Order.from_row(row)
            if not order or order.business_id != business_id:
                continue
            if customer_id and order.customer_id != customer_id:
                continue
            results.append(order)
        return results
