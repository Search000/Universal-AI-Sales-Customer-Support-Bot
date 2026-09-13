"""
Message Pipeline (Phase 4).

INCOMING MESSAGE -> language engine (intent + entities, global knowledge
only) -> knowledge engine (retrieve ONLY matching verified business data)
-> simple safe response.

This is intentionally NOT an AI/LLM call yet — that is Phase 5. This phase
proves the retrieval-before-response discipline: if the business data
doesn't back up a claim, the response says so instead of guessing
(master rules #2 and #3).

Context handling here is in-memory only (lost on restart) — persistent
customer memory is Phase 6.
"""
import logging
from dataclasses import asdict
from typing import Dict, Optional, Tuple

from app.integrations.sheets.repository import BusinessIdRequiredError
from app.services.knowledge_engine import KnowledgeEngine
from app.services.language_engine import Entities, detect_intent, extract_entities
from app.services.response_engine import generate_final_response

logger = logging.getLogger(__name__)

SAFE_FALLBACK = (
    "এই তথ্যটি আমার current business data-তে নেই। "
    "একজন human representative confirm করে দিতে পারবে।"
)

PRODUCT_NOT_FOUND = (
    "আমাদের current product list-এ এই item-টা পাচ্ছি না। "
    "আপনি চাইলে product-এর ছবি পাঠাতে পারেন, আমি দেখে help করতে পারি।"
)


class MessagePipeline:
    def __init__(self, engine: KnowledgeEngine, gemini_client=None):
        self._engine = engine
        # Optional Phase 5 AI client. None = deterministic responses only
        # (this is also what every existing Phase 1-4 test still exercises).
        self._gemini_client = gemini_client
        # in-memory context: (business_id, customer_id) -> last entities
        self._context: Dict[Tuple[str, str], Entities] = {}

    def handle_message(self, business_id: str, customer_id: str, message: str) -> dict:
        if not business_id or not str(business_id).strip():
            raise BusinessIdRequiredError("business_id is required")
        if not message or not message.strip():
            raise ValueError("message is required")

        business = self._engine.get_business(business_id)
        if business is None:
            return {
                "intent": "UNKNOWN",
                "entities": {},
                "retrieved_data": None,
                "confidence": 0.0,
                "response": "এই business_id-এর কোনো তথ্য পাওয়া যায়নি।",
            }

        intent_result = detect_intent(message)
        entities = extract_entities(message)

        ctx_key = (business_id, customer_id or "anonymous")
        if not entities.color and not entities.size and not entities.keywords:
            entities = self._context.get(ctx_key, entities)
        else:
            self._context[ctx_key] = entities

        retrieved_data: Optional[dict] = None
        response: str

        if intent_result.intent in ("PRICE_INQUIRY", "AVAILABILITY_INQUIRY", "PRODUCT_SEARCH"):
            name_hint = entities.keywords[0] if entities.keywords else None
            products = self._engine.find_products(
                business_id, name_contains=name_hint, color=entities.color, size=entities.size
            )
            retrieved_data = {"products": [asdict(p) for p in products]}

            if not products:
                response = PRODUCT_NOT_FOUND
            else:
                product = products[0]
                if intent_result.intent == "PRICE_INQUIRY":
                    response = (
                        f"{product.product_name} ({product.color}, {product.size}) "
                        f"এর দাম {product.price} {product.currency}।"
                    )
                elif intent_result.intent == "AVAILABILITY_INQUIRY":
                    stock = self._engine.get_stock(business_id, product.product_id)
                    if stock and stock.in_stock:
                        response = f"হ্যাঁ, {product.product_name} ({product.color}, {product.size}) স্টকে আছে।"
                    else:
                        response = f"দুঃখিত, {product.product_name} ({product.color}, {product.size}) এখন স্টকে নেই।"
                else:
                    response = (
                        f"{product.product_name} পাওয়া গেছে — দাম {product.price} {product.currency}, "
                        f"স্টক স্ট্যাটাস: {product.stock_status}।"
                    )

        elif intent_result.intent == "POLICY_INQUIRY":
            policy_type = (intent_result.meta or {}).get("policy_type")
            policy = self._engine.get_policy(business_id, policy_type) if policy_type else None
            retrieved_data = {"policy": asdict(policy)} if policy else None
            response = policy.policy_text if policy else SAFE_FALLBACK

        elif intent_result.intent == "GREETING":
            response = f"আসসালামু আলাইকুম! {business.business_name}-এ স্বাগতম। কিভাবে সাহায্য করতে পারি?"

        else:
            response = "দুঃখিত, বুঝতে পারিনি। আরেকটু বিস্তারিত বলবেন কি?"

        final_response = generate_final_response(
            client=self._gemini_client,
            business_name=business.business_name,
            customer_message=message,
            intent=intent_result.intent,
            retrieved_data=retrieved_data,
            draft_response=response,
        )

        return {
            "intent": intent_result.intent,
            "entities": asdict(entities),
            "retrieved_data": retrieved_data,
            "confidence": intent_result.confidence,
            "response": final_response,
        }
