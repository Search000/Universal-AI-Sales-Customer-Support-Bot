import pytest

from app.integrations.sheets.fake_client import FakeSheetsClient
from app.integrations.sheets.repository import SheetsRepository
from app.services.language_engine import Entities
from app.services.memory_service import MemoryService


@pytest.fixture
def memory_service():
    client = FakeSheetsClient({})
    repo = SheetsRepository(client)
    return MemoryService(repo)


def test_load_returns_none_when_nothing_saved(memory_service):
    assert memory_service.load("biz_001", "cust_1") is None


def test_save_then_load_round_trips_entities(memory_service):
    entities = Entities(color="black", size="XL", keywords=["shirt"])
    memory_service.save("biz_001", "cust_1", "PRICE_INQUIRY", entities)

    loaded = memory_service.load("biz_001", "cust_1")
    assert loaded.color == "black"
    assert loaded.size == "XL"
    assert loaded.keywords == ["shirt"]


def test_memory_is_scoped_per_business_and_customer(memory_service):
    memory_service.save("biz_001", "cust_1", "PRICE_INQUIRY", Entities(color="black"))
    memory_service.save("biz_002", "cust_1", "PRICE_INQUIRY", Entities(color="white"))

    assert memory_service.load("biz_001", "cust_1").color == "black"
    assert memory_service.load("biz_002", "cust_1").color == "white"
    assert memory_service.load("biz_001", "cust_2") is None


def test_save_overwrites_previous_memory_for_same_customer(memory_service):
    memory_service.save("biz_001", "cust_1", "PRICE_INQUIRY", Entities(color="black", size="M"))
    memory_service.save("biz_001", "cust_1", "AVAILABILITY_INQUIRY", Entities(color="red", size="L"))

    loaded = memory_service.load("biz_001", "cust_1")
    assert loaded.color == "red"
    assert loaded.size == "L"


def test_new_memory_service_instance_still_sees_saved_data():
    """Simulates an app restart: a fresh MemoryService/repo wrapping the
    SAME underlying data store must still see what was saved earlier."""
    shared_client = FakeSheetsClient({})
    repo1 = SheetsRepository(shared_client)
    MemoryService(repo1).save("biz_001", "cust_1", "PRICE_INQUIRY", Entities(color="black"))

    repo2 = SheetsRepository(shared_client)
    fresh_service = MemoryService(repo2)
    loaded = fresh_service.load("biz_001", "cust_1")
    assert loaded.color == "black"
