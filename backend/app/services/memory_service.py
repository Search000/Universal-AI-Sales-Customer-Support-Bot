"""
Memory Service (Phase 6).

Wraps SheetsRepository's CONVERSATIONS methods so message_pipeline can
remember a customer's last entities (color/size/keywords) and intent
across restarts, instead of the Phase 4 in-memory-only dict that was lost
whenever the app process stopped.

Same isolation rule as everything else: every read/write requires
business_id and is scoped to (business_id, customer_id) — one customer's
memory can never leak into another business's conversation.
"""
import logging
from datetime import datetime, timezone
from typing import Optional

from app.integrations.sheets.repository import SheetsRepository
from app.models.conversation_memory import ConversationMemory
from app.services.language_engine import Entities

logger = logging.getLogger(__name__)


class MemoryService:
    def __init__(self, repository: SheetsRepository):
        self._repo = repository

    def load(self, business_id: str, customer_id: str) -> Optional[Entities]:
        memory = self._repo.get_conversation_memory(business_id, customer_id)
        if memory is None:
            return None
        keywords = [kw for kw in memory.last_keywords.split(",") if kw]
        return Entities(
            color=memory.last_color or None,
            size=memory.last_size or None,
            keywords=keywords,
        )

    def save(self, business_id: str, customer_id: str, intent: str, entities: Entities) -> None:
        try:
            memory = ConversationMemory(
                business_id=business_id,
                customer_id=customer_id,
                last_intent=intent,
                last_color=entities.color or "",
                last_size=entities.size or "",
                last_keywords=",".join(entities.keywords),
                updated_at=datetime.now(timezone.utc).isoformat(),
            )
            self._repo.save_conversation_memory(memory)
        except Exception:
            # Memory is a convenience layer — never let a save failure break
            # the customer's reply.
            logger.exception("Failed to save conversation memory")
