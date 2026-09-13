import pytest

from app.integrations.sheets.fake_client import FakeSheetsClient
from app.integrations.sheets.repository import SheetsRepository, BusinessIdRequiredError
from tests.sample_data import SAMPLE_SHEETS


@pytest.fixture
def repo():
    client = FakeSheetsClient(SAMPLE_SHEETS)
    return SheetsRepository(client)


# ---- business lookup ----------------------------------------------------
def test_business_lookup_found(repo):
    biz = repo.get_business("biz_001")
    assert biz is not None
    assert biz.business_name == "Rupa Fashion"


def test_business_lookup_not_found(repo):
    assert repo.get_business("biz_999") is None


# ---- product lookup ------------------------------------------------------
def test_product_lookup_for_correct_business(repo):
    products = repo.list_products("biz_001")
    assert len(products) == 2
    names = {p.product_name for p in products}
    assert "Black Shirt" in names


def test_product_search_by_color_and_size(repo):
    results = repo.find_products("biz_001", color="black", size="XL")
    assert len(results) == 1
    assert results[0].product_name == "Black Shirt"


# ---- service lookup --------------------------------------------------
def test_service_lookup(repo):
    services = repo.list_services("biz_002")
    assert len(services) == 1
    assert services[0].service_name == "Skin Fade Haircut"


# ---- FAQ lookup -----------------------------------------------------------
def test_faq_lookup(repo):
    faqs = repo.list_faqs("biz_001")
    assert len(faqs) == 1
    assert "delivery" in faqs[0].keywords


# ---- policy lookup ---------------------------------------------------
def test_policy_lookup(repo):
    policy = repo.get_policy("biz_001", "return")
    assert policy is not None
    assert "7 din" in policy.policy_text


# ---- CROSS-BUSINESS ISOLATION (critical) ---------------------------------
def test_business_a_products_never_appear_for_business_b(repo):
    """biz_002 (salon) must get zero products — those belong to biz_001."""
    products = repo.list_products("biz_002")
    assert products == []


def test_business_b_services_never_appear_for_business_a(repo):
    """biz_001 (clothing) must get zero services — those belong to biz_002."""
    services = repo.list_services("biz_001")
    assert services == []


def test_business_a_faq_never_appears_for_business_b(repo):
    assert repo.list_faqs("biz_002") == []


def test_business_a_policy_never_appears_for_business_b(repo):
    assert repo.get_policy("biz_002", "return") is None


# ---- missing business_id must be rejected, never silently allowed --------
def test_missing_business_id_raises():
    client = FakeSheetsClient(SAMPLE_SHEETS)
    repo = SheetsRepository(client)
    with pytest.raises(BusinessIdRequiredError):
        repo.list_products("")
    with pytest.raises(BusinessIdRequiredError):
        repo.get_business(None)
