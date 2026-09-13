from app.integrations.sheets.fake_client import FakeSheetsClient
from app.integrations.sheets.repository import SheetsRepository
from app.services.knowledge_engine import KnowledgeEngine
from app.services.learning_engine import LearningEngine
from app.services.message_pipeline import MessagePipeline
from tests.sample_data import SAMPLE_SHEETS


def _build_pipeline():
    client = FakeSheetsClient(SAMPLE_SHEETS)
    repo = SheetsRepository(client)
    engine = KnowledgeEngine(repo)
    learning = LearningEngine(engine, repo)
    pipeline = MessagePipeline(engine, learning_engine=learning)
    return pipeline, learning


def test_unknown_product_keyword_is_queued_for_learning():
    """The critical test case (master rule #44), extended: Hair Salon has no
    'box' product/service. The AI must not claim one exists AND the unknown
    word should be queued for owner review, not silently dropped and not
    auto-created as a fact."""
    pipeline, learning = _build_pipeline()

    result = pipeline.handle_message("biz_002", "cust_1", "লাল box আছে?")

    assert "box" not in result["response"].lower() or "নেই" in result["response"] or "পাচ্ছি না" in result["response"]
    pending = learning.list_pending("biz_002")
    terms = [e.term.lower() for e in pending]
    assert "box" in terms


def test_learning_queue_stays_isolated_per_business_via_pipeline():
    pipeline, learning = _build_pipeline()
    pipeline.handle_message("biz_002", "cust_1", "লাল box আছে?")

    # Business A never saw this conversation — must have nothing queued.
    assert learning.list_pending("biz_001") == []


def test_known_product_search_does_not_pollute_learning_queue():
    pipeline, learning = _build_pipeline()
    pipeline.handle_message("biz_001", "cust_1", "black shirt price koto?")

    assert learning.list_pending("biz_001") == []


def test_pipeline_without_learning_engine_still_works():
    client = FakeSheetsClient(SAMPLE_SHEETS)
    repo = SheetsRepository(client)
    engine = KnowledgeEngine(repo)
    pipeline = MessagePipeline(engine)  # no learning_engine wired

    # Must not raise even though no learning engine is present.
    result = pipeline.handle_message("biz_002", "cust_1", "লাল box আছে?")
    assert result["response"]
