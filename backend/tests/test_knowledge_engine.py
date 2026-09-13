import pytest

from app.integrations.sheets.fake_client import FakeSheetsClient
from app.integrations.sheets.repository import SheetsRepository
from app.services.knowledge_engine import KnowledgeEngine
from tests.sample_data import SAMPLE_SHEETS


@pytest.fixture
def engine():
    client = FakeSheetsClient(SAMPLE_SHEETS)
    repo = SheetsRepository(client)
    return KnowledgeEngine(repo)


# ---- product / stock / price ---------------------------------------------
def test_find_products_by_attributes(engine):
    results = engine.find_products("biz_001", color="black", size="XL")
    assert len(results) == 1
    assert results[0].product_name == "Black Shirt"


def test_get_stock_known_product(engine):
    stock = engine.get_stock("biz_001", "prod_001")
    assert stock is not None
    assert stock.in_stock is True
    assert stock.stock_count == 10


def test_get_stock_unknown_product_returns_none_not_guess(engine):
    assert engine.get_stock("biz_001", "prod_999") is None


def test_get_price_known_product(engine):
    assert engine.get_price("biz_001", "prod_001") == "1200"


def test_get_price_unknown_product_returns_none(engine):
    assert engine.get_price("biz_001", "prod_999") is None


# ---- business rules --------------------------------------------------
def test_get_business_rule(engine):
    rule = engine.get_business_rule("biz_001", "cod_allowed")
    assert rule is not None
    assert rule.rule_value == "TRUE"


def test_business_rule_isolation(engine):
    """biz_001's cod_allowed rule must not appear when asking as biz_002."""
    assert engine.get_business_rule("biz_002", "cod_allowed") is None


# ---- vocabulary (business-specific terms must never cross over) ---------
def test_vocabulary_resolves_for_owning_business(engine):
    vocab = engine.resolve_vocabulary("biz_001", "boxy")
    assert vocab is not None
    assert "shirt" in vocab.meaning


def test_vocabulary_term_from_other_business_not_resolved(engine):
    """'fade' is Style Cuts Salon's (biz_002) vocabulary — Rupa Fashion
    (biz_001) must NOT resolve it, even though the term technically exists
    in the spreadsheet for a different business."""
    assert engine.resolve_vocabulary("biz_001", "fade") is None


def test_vocabulary_term_boxy_not_resolved_for_salon(engine):
    assert engine.resolve_vocabulary("biz_002", "boxy") is None


# ---- FAQ / services isolation via knowledge engine -----------------------
def test_faq_search_isolated(engine):
    assert engine.search_faq("biz_002", "delivery") == []
    assert len(engine.search_faq("biz_001", "delivery")) == 1


def test_service_search_isolated(engine):
    assert engine.find_services("biz_001") == []
    assert len(engine.find_services("biz_002")) == 1
