import pytest

from app.integrations.sheets.fake_client import FakeSheetsClient
from app.integrations.sheets.repository import SheetsRepository
from app.services.knowledge_engine import KnowledgeEngine
from app.services.learning_engine import LearningEngine, LearningEngineError
from tests.sample_data import SAMPLE_SHEETS


@pytest.fixture
def learning_setup():
    client = FakeSheetsClient(SAMPLE_SHEETS)
    repo = SheetsRepository(client)
    engine = KnowledgeEngine(repo)
    learning = LearningEngine(engine, repo)
    return learning, repo


# ---- detection ---------------------------------------------------------
def test_known_product_word_is_not_flagged(learning_setup):
    learning, _ = learning_setup
    unknown = learning.find_unrecognized_keywords("biz_001", ["shirt", "black"])
    assert "shirt" not in unknown


def test_approved_vocabulary_word_is_not_flagged(learning_setup):
    learning, _ = learning_setup
    unknown = learning.find_unrecognized_keywords("biz_001", ["boxy"])
    assert unknown == []


def test_genuinely_unknown_word_is_flagged(learning_setup):
    learning, _ = learning_setup
    unknown = learning.find_unrecognized_keywords("biz_001", ["box"])
    assert unknown == ["box"]


def test_salon_specific_word_unknown_for_clothing_business(learning_setup):
    """'fade' is only meaningful/approved for biz_002 (salon) -- for the
    clothing business it must still be treated as unrecognized."""
    learning, _ = learning_setup
    unknown = learning.find_unrecognized_keywords("biz_001", ["fade"])
    assert unknown == ["fade"]


# ---- queueing: never auto-creates a fact --------------------------------
def test_record_unknown_term_queues_as_pending_only(learning_setup):
    learning, repo = learning_setup
    learning.record_unknown_term("biz_001", "box", context="আমার লাল box লাগবে")

    pending = learning.list_pending("biz_001")
    assert len(pending) == 1
    assert pending[0].term == "box"
    assert pending[0].status == "pending"

    # Critically: no vocabulary was created from this alone.
    assert repo.resolve_vocabulary_term("biz_001", "box") is None


def test_repeated_unknown_term_does_not_duplicate_queue_entries(learning_setup):
    learning, _ = learning_setup
    learning.record_unknown_term("biz_001", "box")
    learning.record_unknown_term("biz_001", "box")
    learning.record_unknown_term("biz_001", "box")

    pending = learning.list_pending("biz_001")
    assert len(pending) == 1


def test_learning_queue_is_isolated_per_business(learning_setup):
    learning, _ = learning_setup
    learning.record_unknown_term("biz_001", "box")
    assert learning.list_pending("biz_002") == []


# ---- approval: the only path that creates trusted vocabulary -----------
def test_approve_creates_approved_vocabulary_entry(learning_setup):
    learning, repo = learning_setup
    entry = learning.record_unknown_term("biz_001", "box", context="customer asked about box")

    vocab = learning.approve(
        "biz_001", entry.learning_id, meaning="gift box", category="accessory"
    )
    assert vocab.approved == "TRUE"
    assert vocab.term == "box"

    resolved = repo.resolve_vocabulary_term("biz_001", "box")
    assert resolved is not None
    assert resolved.meaning == "gift box"


def test_approve_marks_entry_approved_and_not_pending_anymore(learning_setup):
    learning, _ = learning_setup
    entry = learning.record_unknown_term("biz_001", "box")
    learning.approve("biz_001", entry.learning_id, meaning="gift box")

    assert learning.list_pending("biz_001") == []


def test_approve_without_meaning_is_rejected(learning_setup):
    learning, _ = learning_setup
    entry = learning.record_unknown_term("biz_001", "box")
    with pytest.raises(LearningEngineError):
        learning.approve("biz_001", entry.learning_id, meaning="")


def test_approve_unknown_learning_id_raises(learning_setup):
    learning, _ = learning_setup
    with pytest.raises(LearningEngineError):
        learning.approve("biz_001", "lrn_does_not_exist", meaning="whatever")


def test_double_approve_raises(learning_setup):
    learning, _ = learning_setup
    entry = learning.record_unknown_term("biz_001", "box")
    learning.approve("biz_001", entry.learning_id, meaning="gift box")
    with pytest.raises(LearningEngineError):
        learning.approve("biz_001", entry.learning_id, meaning="gift box again")


# ---- rejection -----------------------------------------------------------
def test_reject_closes_entry_without_creating_vocabulary(learning_setup):
    learning, repo = learning_setup
    entry = learning.record_unknown_term("biz_001", "box")
    rejected = learning.reject("biz_001", entry.learning_id)

    assert rejected.status == "rejected"
    assert learning.list_pending("biz_001") == []
    assert repo.resolve_vocabulary_term("biz_001", "box") is None


def test_reject_unknown_learning_id_raises(learning_setup):
    learning, _ = learning_setup
    with pytest.raises(LearningEngineError):
        learning.reject("biz_001", "lrn_does_not_exist")
