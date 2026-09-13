import pytest

from app.integrations.gemini.fake_client import FakeGeminiClient
from app.integrations.sheets.fake_client import FakeSheetsClient
from app.integrations.sheets.repository import SheetsRepository, BusinessIdRequiredError
from app.services.knowledge_engine import KnowledgeEngine
from app.services.memory_service import MemoryService
from app.services.message_pipeline import MessagePipeline, PRODUCT_NOT_FOUND
from tests.sample_data import SAMPLE_SHEETS


@pytest.fixture
def pipeline():
    client = FakeSheetsClient(SAMPLE_SHEETS)
    repo = SheetsRepository(client)
    engine = KnowledgeEngine(repo)
    return MessagePipeline(engine)


def test_no_gemini_client_still_works_deterministically(pipeline):
    """Phase 1-4 behavior must be untouched when no AI client is wired."""
    result = pipeline.handle_message("biz_001", "cust_1", "black shirt price koto?")
    assert "1200" in result["response"]


def test_gemini_client_rephrases_when_data_is_grounded():
    client = FakeSheetsClient(SAMPLE_SHEETS)
    repo = SheetsRepository(client)
    engine = KnowledgeEngine(repo)
    fake_gemini = FakeGeminiClient(canned_response="AI phrased reply")
    pipeline_with_ai = MessagePipeline(engine, gemini_client=fake_gemini)

    result = pipeline_with_ai.handle_message("biz_001", "cust_1", "black shirt price koto?")
    assert result["response"] == "AI phrased reply"


def test_gemini_client_not_used_when_no_data_found():
    client = FakeSheetsClient(SAMPLE_SHEETS)
    repo = SheetsRepository(client)
    engine = KnowledgeEngine(repo)
    fake_gemini = FakeGeminiClient(canned_response="should never appear")
    pipeline_with_ai = MessagePipeline(engine, gemini_client=fake_gemini)

    result = pipeline_with_ai.handle_message("biz_002", "cust_1", "return policy ki?")
    assert result["response"] != "should never appear"


def test_memory_service_persists_context_across_pipeline_restarts():
    """Without memory_service, a new MessagePipeline instance forgets
    everything (old Phase 4 behavior). With memory_service wired to a
    shared underlying store, a 'restarted' pipeline still remembers."""
    shared_client = FakeSheetsClient(SAMPLE_SHEETS)

    repo1 = SheetsRepository(shared_client)
    engine1 = KnowledgeEngine(repo1)
    memory1 = MemoryService(repo1)
    pipeline1 = MessagePipeline(engine1, memory_service=memory1)
    pipeline1.handle_message("biz_001", "cust_1", "black shirt ache?")

    # Simulate a restart: brand new engine/pipeline objects, same backing store.
    repo2 = SheetsRepository(shared_client)
    engine2 = KnowledgeEngine(repo2)
    memory2 = MemoryService(repo2)
    pipeline2 = MessagePipeline(engine2, memory_service=memory2)

    result = pipeline2.handle_message("biz_001", "cust_1", "koto dam?")
    assert result["intent"] == "PRICE_INQUIRY"
    assert "black" in result["entities"]["color"].lower() if result["entities"]["color"] else False
    assert "1200" in result["response"]


def test_price_inquiry_returns_verified_price(pipeline):
    result = pipeline.handle_message("biz_001", "cust_1", "black shirt price koto?")
    assert result["intent"] == "PRICE_INQUIRY"
    assert "1200" in result["response"]
    assert result["retrieved_data"]["products"][0]["product_name"] == "Black Shirt"


def test_availability_inquiry_in_stock(pipeline):
    result = pipeline.handle_message("biz_001", "cust_1", "black shirt XL আছে?")
    assert result["intent"] == "AVAILABILITY_INQUIRY"
    assert "আছে" in result["response"]


def test_policy_inquiry_returns_verified_policy(pipeline):
    result = pipeline.handle_message("biz_001", "cust_1", "return policy ki?")
    assert result["intent"] == "POLICY_INQUIRY"
    assert "7 din" in result["response"]


def test_policy_inquiry_missing_data_safe_fallback(pipeline):
    """biz_002 has no 'return' policy row — must not invent one."""
    result = pipeline.handle_message("biz_002", "cust_1", "return policy ki?")
    assert result["retrieved_data"] is None
    assert "নেই" in result["response"]


def test_greeting(pipeline):
    result = pipeline.handle_message("biz_001", "cust_1", "Assalamualaikum")
    assert result["intent"] == "GREETING"
    assert "Rupa Fashion" in result["response"]


def test_missing_business_returns_safe_message(pipeline):
    result = pipeline.handle_message("biz_999", "cust_1", "price koto")
    assert result["intent"] == "UNKNOWN"
    assert result["retrieved_data"] is None


def test_missing_business_id_raises(pipeline):
    with pytest.raises(BusinessIdRequiredError):
        pipeline.handle_message("", "cust_1", "hi")


def test_empty_message_raises(pipeline):
    with pytest.raises(ValueError):
        pipeline.handle_message("biz_001", "cust_1", "   ")


# ---- THE MASTER-PROMPT HALLUCINATION TEST (section 2) --------------------
def test_language_understanding_never_becomes_business_fact(pipeline):
    """
    Customer: 'ভাই আমার লাল box না কালোটা লাগবে'
    The AI understands লাল=red, কালো=black, and 'box' as a product word —
    but Rupa Fashion (biz_001) sells shirts/panjabi, NOT boxes.
    The response must NOT confirm a box exists. It must say the item
    wasn't found, not fabricate availability/price/color for it.
    """
    result = pipeline.handle_message("biz_001", "cust_1", "ভাই আমার লাল box না কালোটা লাগবে")

    assert result["entities"]["color"] == "black"  # language understanding worked
    assert result["retrieved_data"]["products"] == []  # nothing invented
    assert result["response"] == PRODUCT_NOT_FOUND  # safe fallback, not a guess


# ---- cross-business isolation through the full pipeline ------------------
def test_pipeline_isolation_across_businesses(pipeline):
    """Asking biz_002 (salon) about a biz_001 (clothing) product must fail safe."""
    result = pipeline.handle_message("biz_002", "cust_1", "black shirt price koto?")
    assert result["retrieved_data"]["products"] == []
    assert result["response"] == PRODUCT_NOT_FOUND


# ---- Phase 7: order intent -------------------------------------------------
def test_order_intent_without_order_engine_gives_safe_fallback(pipeline):
    result = pipeline.handle_message("biz_001", "cust_1", "black shirt order korte chai")
    assert result["intent"] == "ORDER_INTENT"
    assert "না" in result["response"] or "not" in result["response"].lower()


def test_order_intent_with_order_engine_creates_order():
    from app.services.order_engine import OrderEngine

    client = FakeSheetsClient(SAMPLE_SHEETS)
    repo = SheetsRepository(client)
    engine = KnowledgeEngine(repo)
    order_engine = OrderEngine(engine, repo)
    pipeline_with_orders = MessagePipeline(engine, order_engine=order_engine)

    result = pipeline_with_orders.handle_message("biz_001", "cust_1", "black shirt 1ta order korte chai")
    assert result["intent"] == "ORDER_INTENT"
    assert "Order ID" in result["response"]
    assert result["retrieved_data"]["order"]["product_id"] == "prod_001"


def test_order_intent_remembers_product_from_previous_turn():
    from app.services.order_engine import OrderEngine
    from app.services.memory_service import MemoryService

    client = FakeSheetsClient(SAMPLE_SHEETS)
    repo = SheetsRepository(client)
    engine = KnowledgeEngine(repo)
    order_engine = OrderEngine(engine, repo)
    memory_service = MemoryService(repo)
    pipeline_with_orders = MessagePipeline(
        engine, order_engine=order_engine, memory_service=memory_service
    )

    pipeline_with_orders.handle_message("biz_001", "cust_1", "black shirt XL koto?")
    result = pipeline_with_orders.handle_message("biz_001", "cust_1", "order korte chai")

    assert result["intent"] == "ORDER_INTENT"
    assert "Order ID" in result["response"]
