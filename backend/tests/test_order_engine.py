import pytest

from app.integrations.sheets.fake_client import FakeSheetsClient
from app.integrations.sheets.repository import SheetsRepository
from app.services.knowledge_engine import KnowledgeEngine
from app.services.order_engine import OrderEngine
from tests.sample_data import SAMPLE_SHEETS


@pytest.fixture
def order_engine():
    client = FakeSheetsClient(SAMPLE_SHEETS)
    repo = SheetsRepository(client)
    engine = KnowledgeEngine(repo)
    return OrderEngine(engine, repo), repo


def test_place_order_for_in_stock_product_succeeds(order_engine):
    engine, repo = order_engine
    result = engine.place_order("biz_001", "cust_1", "prod_001", quantity=2)

    assert result.error is None
    assert result.order is not None
    assert result.order.product_name == "Black Shirt"
    assert result.order.quantity == 2
    assert result.order.total_price == "2400.0"


def test_order_is_persisted_and_listable(order_engine):
    engine, repo = order_engine
    engine.place_order("biz_001", "cust_1", "prod_001", quantity=1)

    orders = engine.list_customer_orders("biz_001", "cust_1")
    assert len(orders) == 1
    assert orders[0].product_id == "prod_001"


def test_unknown_product_is_refused_not_guessed(order_engine):
    engine, repo = order_engine
    result = engine.place_order("biz_001", "cust_1", "prod_does_not_exist", quantity=1)

    assert result.order is None
    assert result.error == "PRODUCT_NOT_FOUND"


def test_product_from_wrong_business_is_refused(order_engine):
    """prod_001 belongs to biz_001 — biz_002 must never be able to order it."""
    engine, repo = order_engine
    result = engine.place_order("biz_002", "cust_1", "prod_001", quantity=1)

    assert result.order is None
    assert result.error == "PRODUCT_NOT_FOUND"


def test_zero_quantity_is_refused(order_engine):
    engine, repo = order_engine
    result = engine.place_order("biz_001", "cust_1", "prod_001", quantity=0)

    assert result.order is None
    assert result.error is not None
