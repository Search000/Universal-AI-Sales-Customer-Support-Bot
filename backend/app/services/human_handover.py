"""
Human Handover Engine (Phase 9).

Decides whether a conversation should be flagged human_required, per master
rule #20. Handover triggers:
  - explicit human request ("human", "কাউকে দেন", etc.)
  - angry/upset customer language
  - unsupported request (e.g. order placement not wired up yet)
  - business data genuinely unavailable (safe-fallback / product-not-found
    replies) -- master rule #20 lists "unavailable business information"
    as its own trigger, separate from low confidence
  - repeated misunderstanding (same customer hits an unresolved reply
    several turns in a row)

This module only decides yes/no + reason. It never changes what the
customer is told about business facts -- that discipline stays entirely
in knowledge_engine / response_engine.
"""
from dataclasses import dataclass
from typing import Optional

UNRESOLVED_THRESHOLD = 2  # consecutive unresolved turns before escalating

HANDOVER_MESSAGE = (
    "জি, আপনার বিষয়টি একজন human representative-কে জানানো হচ্ছে। "
    "তিনি শীঘ্রই আপনার সাথে যোগাযোগ করবেন।"
)


@dataclass
class HandoverDecision:
    required: bool
    reason: Optional[str] = None


def evaluate(
    intent: str,
    intent_meta: Optional[dict] = None,
    unsupported: bool = False,
    data_unavailable: bool = False,
    unresolved_count: int = 0,
) -> HandoverDecision:
    if intent == "HUMAN_HANDOVER":
        reason = (intent_meta or {}).get("reason", "human_request")
        return HandoverDecision(True, reason)

    if unsupported:
        return HandoverDecision(True, "unsupported_request")

    if data_unavailable:
        return HandoverDecision(True, "business_data_unavailable")

    if unresolved_count >= UNRESOLVED_THRESHOLD:
        return HandoverDecision(True, "repeated_misunderstanding")

    return HandoverDecision(False, None)
