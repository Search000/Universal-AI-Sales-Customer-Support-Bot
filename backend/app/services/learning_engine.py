"""
Learning Engine (Phase 8).

Purpose: let the system notice words it doesn't understand for THIS
business, without ever treating a customer's message as a trusted
business fact (master rules #6 and #7).

Flow:
    unknown keyword in customer message
        -> not a known product/service word, not already-approved vocabulary
        -> record_unknown_term() queues it as pending
        -> business owner reviews via /learning routes
        -> approve() writes an approved VOCABULARY row (only path that
           creates trusted vocabulary)
        -> reject()/ignore() close the entry without creating anything

The queue never auto-promotes itself. No code path other than approve()
is allowed to write to VOCABULARY.
"""
import logging
from datetime import datetime, timezone
from typing import List, Optional

from app.integrations.sheets.repository import SheetsRepository
from app.models.learning_queue import LearningQueueEntry
from app.models.vocabulary import Vocabulary
from app.services.knowledge_engine import KnowledgeEngine

logger = logging.getLogger(__name__)


class LearningEngineError(ValueError):
    """Raised for invalid learning-queue operations (e.g. approving an
    entry that doesn't exist or was already reviewed)."""


class LearningEngine:
    def __init__(self, knowledge_engine: KnowledgeEngine, repository: SheetsRepository):
        self._engine = knowledge_engine
        self._repo = repository

    # ---- detection ---------------------------------------------------
    def find_unrecognized_keywords(
        self, business_id: str, keywords: List[str]
    ) -> List[str]:
        """Of the candidate keywords the language engine pulled out of a
        message, return the ones that don't match any known product name,
        service name, or already-approved business vocabulary. These are
        candidates for the learning queue — NOT confirmed facts."""
        if not keywords:
            return []

        products = self._engine.find_products(business_id)
        services = self._engine.find_services(business_id)
        product_words = {
            w.lower() for p in products for w in p.product_name.split()
        }
        service_words = {
            w.lower() for s in services for w in s.service_name.split()
        }

        unrecognized = []
        for kw in keywords:
            low = kw.lower()
            if low in product_words or low in service_words:
                continue
            if self._engine.resolve_vocabulary(business_id, kw) is not None:
                continue
            unrecognized.append(kw)
        return unrecognized

    # ---- queueing ------------------------------------------------------
    def record_unknown_term(
        self,
        business_id: str,
        term: str,
        context: str = "",
        possible_meaning: str = "",
        confidence: float = 0.5,
        source: str = "customer_message",
    ) -> LearningQueueEntry:
        """Queue an unknown term for owner review. If a pending entry for
        this exact business+term already exists, do nothing new — we don't
        want the queue flooded with duplicates every time a customer
        repeats the same unknown word (master rule #7: many repetitions of
        a customer claim still don't make it a fact)."""
        existing = [
            e
            for e in self._repo.list_learning_queue(business_id, status="pending")
            if e.term.lower() == term.lower()
        ]
        if existing:
            return existing[0]

        entry = LearningQueueEntry(
            learning_id=LearningQueueEntry.new_id(),
            business_id=business_id,
            term=term,
            possible_meaning=possible_meaning,
            context=context,
            confidence=str(confidence),
            source=source,
            status="pending",
            created_at=datetime.now(timezone.utc).isoformat(),
        )
        self._repo.create_learning_entry(entry)
        logger.info("Learning queue: new pending term '%s' for %s", term, business_id)
        return entry

    # ---- review ----------------------------------------------------------
    def list_pending(self, business_id: str) -> List[LearningQueueEntry]:
        return self._repo.list_learning_queue(business_id, status="pending")

    def approve(
        self,
        business_id: str,
        learning_id: str,
        meaning: str,
        category: str = "",
        approved_by: str = "owner",
    ) -> Vocabulary:
        """The ONLY path that turns a learned term into trusted business
        vocabulary — and it requires an explicit human-provided meaning,
        never the raw customer message."""
        entry = self._repo.get_learning_entry(business_id, learning_id)
        if entry is None:
            raise LearningEngineError("LEARNING_ENTRY_NOT_FOUND")
        if entry.status != "pending":
            raise LearningEngineError(f"ENTRY_ALREADY_{entry.status.upper()}")
        if not meaning or not meaning.strip():
            raise LearningEngineError("MEANING_REQUIRED")

        now = datetime.now(timezone.utc).isoformat()
        vocab = Vocabulary(
            vocab_id=Vocabulary.new_id(),
            business_id=business_id,
            term=entry.term,
            meaning=meaning,
            category=category,
            examples=entry.context,
            approved="TRUE",
            updated_at=now,
        )
        self._repo.save_vocabulary(vocab)

        entry.status = "approved"
        entry.approved_by = approved_by
        entry.approved_at = now
        entry.reviewed_at = now
        self._repo.update_learning_entry(entry)
        logger.info("Learning queue: approved '%s' for %s -> vocabulary", entry.term, business_id)
        return vocab

    def reject(
        self, business_id: str, learning_id: str, reviewed_by: str = "owner"
    ) -> LearningQueueEntry:
        entry = self._repo.get_learning_entry(business_id, learning_id)
        if entry is None:
            raise LearningEngineError("LEARNING_ENTRY_NOT_FOUND")
        if entry.status != "pending":
            raise LearningEngineError(f"ENTRY_ALREADY_{entry.status.upper()}")

        entry.status = "rejected"
        entry.approved_by = reviewed_by
        entry.reviewed_at = datetime.now(timezone.utc).isoformat()
        self._repo.update_learning_entry(entry)
        logger.info("Learning queue: rejected '%s' for %s", entry.term, business_id)
        return entry
