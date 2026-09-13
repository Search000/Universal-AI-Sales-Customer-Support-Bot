from app.integrations.sheets.fake_client import FakeSheetsClient
from app.integrations.sheets.repository import SheetsRepository
from app.services.knowledge_engine import KnowledgeEngine
from app.services.memory_service import MemoryService
from app.services.message_pipeline import MessagePipeline
from tests.sample_data import SAMPLE_SHEETS


def _build_pipeline(with_memory=False):
    client = FakeSheetsClient(SAMPLE_SHEETS)
    repo = SheetsRepository(client)
    engine = KnowledgeEngine(repo)
    memory_service = MemoryService(repo) if with_memory else None
    pipeline = MessagePipeline(engine, memory_service=memory_service)
    return pipeline


def test_explicit_human_request_flags_human_required():
    pipeline = _build_pipeline()
    result = pipeline.handle_message("biz_001", "cust_1", "ভাই কাউকে দেন")

    assert result["human_required"] is True
    assert result["human_required_reason"] == "human_request"


def test_angry_message_flags_human_required():
    pipeline = _build_pipeline()
    result = pipeline.handle_message("biz_001", "cust_1", "সার্ভিস খারাপ, রিফান্ড দেন")

    assert result["human_required"] is True
    assert result["human_required_reason"] == "angry_customer"


def test_normal_resolved_message_does_not_flag_human_required():
    pipeline = _build_pipeline()
    result = pipeline.handle_message("biz_001", "cust_1", "black shirt price koto?")

    assert result["human_required"] is False


def test_order_unsupported_flags_human_required():
    """No order_engine wired -> ORDER_NOT_AVAILABLE -> unsupported request."""
    pipeline = _build_pipeline()
    result = pipeline.handle_message("biz_001", "cust_1", "এইটা অর্ডার করতে চাই")

    assert result["human_required"] is True
    assert result["human_required_reason"] == "unsupported_request"


def test_missing_policy_flags_human_required_immediately():
    """biz_002 (salon) has no POLICIES rows at all -> SAFE_FALLBACK, which is
    treated as an immediate handover trigger (we flatly don't have this
    fact), unlike a plain product-not-found miss."""
    pipeline = _build_pipeline()
    result = pipeline.handle_message("biz_002", "cust_1", "return policy ki?")

    assert result["human_required"] is True
    assert result["human_required_reason"] == "business_data_unavailable"


def test_single_product_not_found_does_not_immediately_escalate():
    pipeline = _build_pipeline()
    result = pipeline.handle_message("biz_002", "cust_1", "black shirt koto?")

    assert result["human_required"] is False


def test_repeated_unresolved_messages_escalate_with_memory():
    pipeline = _build_pipeline(with_memory=True)

    r1 = pipeline.handle_message("biz_001", "cust_1", "asdkjaslkdj")
    assert r1["human_required"] is False  # first unresolved turn, not yet escalated

    r2 = pipeline.handle_message("biz_001", "cust_1", "qweqweqwe")
    assert r2["human_required"] is True
    assert r2["human_required_reason"] == "repeated_misunderstanding"


def test_resolving_a_message_resets_the_unresolved_streak():
    pipeline = _build_pipeline(with_memory=True)

    pipeline.handle_message("biz_001", "cust_1", "asdkjaslkdj")
    resolved = pipeline.handle_message("biz_001", "cust_1", "black shirt price koto?")
    assert resolved["human_required"] is False

    # streak should be reset — one more unresolved turn shouldn't escalate yet
    r3 = pipeline.handle_message("biz_001", "cust_1", "zxczxczxc")
    assert r3["human_required"] is False


def test_human_handover_isolated_per_customer():
    pipeline = _build_pipeline(with_memory=True)
    pipeline.handle_message("biz_001", "cust_1", "ভাই কাউকে দেন")

    other_customer = pipeline.handle_message("biz_001", "cust_2", "black shirt price koto?")
    assert other_customer["human_required"] is False
