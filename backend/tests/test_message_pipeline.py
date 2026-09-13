import pytest

from app.integrations.sheets.fake_client import FakeSheetsClient
from app.integrations.sheets.repository import SheetsRepository, BusinessIdRequiredError
from app.services.knowledge_engine import KnowledgeEngine
from app.services.message_pipeline import MessagePipeline, PRODUCT_NOT_FOUND
from tests.sample_data import SAMPLE_SHEETS


@pytest.fixture
def pipeline():
    client = FakeSheetsClient(SAMPLE_SHEETS)
    repo = SheetsRepository(client)
    engine = KnowledgeEngine(repo)
    return MessagePipeline(engine)


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
