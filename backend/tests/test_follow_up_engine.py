import copy
from datetime import datetime, timedelta, timezone

import pytest

from app.integrations.sheets.fake_client import FakeSheetsClient
from app.integrations.sheets.repository import SheetsRepository
from app.services.follow_up_engine import FollowUpEngine
from tests.sample_data import SAMPLE_SHEETS


def _sheets():
    """A richer local copy of the sample data: two shirts in the same
    category (for recommendation/upsell tests), plus conversation and
    order rows the base sample data doesn't have."""
    sheets = copy.deepcopy(SAMPLE_SHEETS)
    sheets["PRODUCTS"].append(
        {
            "product_id": "prod_003",
            "business_id": "biz_001",
            "product_name": "White Shirt",
            "description": "",
            "category": "shirt",
            "price": "1500",
            "currency": "BDT",
            "stock": "8",
            "stock_status": "in_stock",
            "size": "L",
            "color": "white",
            "variant": "",
            "sku": "SKU-003",
            "image_url": "",
            "delivery_available": "TRUE",
            "active": "TRUE",
            "updated_at": "2026-01-01",
        }
    )
    return sheets


def _engine(sheets=None):
    client = FakeSheetsClient(sheets or _sheets())
    repo = SheetsRepository(client)
    return FollowUpEngine(repo), repo


def test_default_config_used_when_no_business_rules_set():
    engine, _ = _engine()
    config = engine.get_config("biz_001")
    assert config["follow_up_enabled"] == "TRUE"
    assert config["abandoned_conversation_hours"] == "6"


def test_business_rule_overrides_default():
    sheets = _sheets()
    sheets["BUSINESS_RULES"].append(
        {
            "rule_id": "rule_010",
            "business_id": "biz_001",
            "rule_name": "abandoned_conversation_hours",
            "rule_value": "2",
            "priority": "1",
            "active": "TRUE",
            "updated_at": "2026-01-01",
        }
    )
    engine, _ = _engine(sheets)
    assert engine.get_config("biz_001")["abandoned_conversation_hours"] == "2"


def test_inactive_business_rule_is_ignored():
    sheets = _sheets()
    sheets["BUSINESS_RULES"].append(
        {
            "rule_id": "rule_011",
            "business_id": "biz_001",
            "rule_name": "follow_up_enabled",
            "rule_value": "FALSE",
            "priority": "1",
            "active": "FALSE",
            "updated_at": "2026-01-01",
        }
    )
    engine, _ = _engine(sheets)
    assert engine.is_follow_up_enabled("biz_001") is True


def test_detect_abandoned_conversations_past_threshold():
    now = datetime.now(timezone.utc)
    old_time = (now - timedelta(hours=10)).isoformat()
    recent_time = (now - timedelta(hours=1)).isoformat()

    sheets = _sheets()
    sheets["CONVERSATIONS"] = [
        {
            "business_id": "biz_001",
            "customer_id": "cust_old",
            "last_intent": "price_inquiry",
            "last_color": "",
            "last_size": "",
            "last_keywords": "",
            "unresolved_count": "0",
            "human_required": "FALSE",
            "human_required_reason": "",
            "updated_at": old_time,
        },
        {
            "business_id": "biz_001",
            "customer_id": "cust_recent",
            "last_intent": "price_inquiry",
            "last_color": "",
            "last_size": "",
            "last_keywords": "",
            "unresolved_count": "0",
            "human_required": "FALSE",
            "human_required_reason": "",
            "updated_at": recent_time,
        },
    ]
    engine, _ = _engine(sheets)
    results = engine.detect_abandoned_conversations("biz_001", now=now)

    assert len(results) == 1
    assert results[0].customer_id == "cust_old"


def test_conversation_needing_human_is_never_a_follow_up_target():
    now = datetime.now(timezone.utc)
    old_time = (now - timedelta(hours=10)).isoformat()
    sheets = _sheets()
    sheets["CONVERSATIONS"] = [
        {
            "business_id": "biz_001",
            "customer_id": "cust_escalated",
            "last_intent": "complaint",
            "last_color": "",
            "last_size": "",
            "last_keywords": "",
            "unresolved_count": "3",
            "human_required": "TRUE",
            "human_required_reason": "angry customer",
            "updated_at": old_time,
        }
    ]
    engine, _ = _engine(sheets)
    results = engine.detect_abandoned_conversations("biz_001", now=now)
    assert results == []


def test_abandoned_conversations_respects_business_isolation():
    now = datetime.now(timezone.utc)
    old_time = (now - timedelta(hours=10)).isoformat()
    sheets = _sheets()
    sheets["CONVERSATIONS"] = [
        {
            "business_id": "biz_002",
            "customer_id": "cust_other_biz",
            "last_intent": "price_inquiry",
            "last_color": "",
            "last_size": "",
            "last_keywords": "",
            "unresolved_count": "0",
            "human_required": "FALSE",
            "human_required_reason": "",
            "updated_at": old_time,
        }
    ]
    engine, _ = _engine(sheets)
    assert engine.detect_abandoned_conversations("biz_001", now=now) == []


def test_detect_abandoned_orders_excludes_completed_and_recent():
    now = datetime.now(timezone.utc)
    old_time = (now - timedelta(hours=48)).isoformat()
    recent_time = (now - timedelta(hours=1)).isoformat()
    sheets = _sheets()
    sheets["ORDERS"] = [
        {
            "order_id": "ord_old_pending",
            "business_id": "biz_001",
            "customer_id": "cust_1",
            "product_id": "prod_001",
            "product_name": "Black Shirt",
            "quantity": "1",
            "unit_price": "1200",
            "total_price": "1200",
            "currency": "BDT",
            "status": "pending",
            "created_at": old_time,
        },
        {
            "order_id": "ord_old_completed",
            "business_id": "biz_001",
            "customer_id": "cust_1",
            "product_id": "prod_001",
            "product_name": "Black Shirt",
            "quantity": "1",
            "unit_price": "1200",
            "total_price": "1200",
            "currency": "BDT",
            "status": "completed",
            "created_at": old_time,
        },
        {
            "order_id": "ord_recent_pending",
            "business_id": "biz_001",
            "customer_id": "cust_1",
            "product_id": "prod_001",
            "product_name": "Black Shirt",
            "quantity": "1",
            "unit_price": "1200",
            "total_price": "1200",
            "currency": "BDT",
            "status": "pending",
            "created_at": recent_time,
        },
    ]
    engine, _ = _engine(sheets)
    results = engine.detect_abandoned_orders("biz_001", now=now)

    assert len(results) == 1
    assert results[0].order.order_id == "ord_old_pending"


def test_recommend_products_uses_order_history_category():
    sheets = _sheets()
    sheets["ORDERS"] = [
        {
            "order_id": "ord_1",
            "business_id": "biz_001",
            "customer_id": "cust_1",
            "product_id": "prod_001",
            "product_name": "Black Shirt",
            "quantity": "1",
            "unit_price": "1200",
            "total_price": "1200",
            "currency": "BDT",
            "status": "completed",
            "created_at": "2026-01-01T00:00:00+00:00",
        }
    ]
    engine, _ = _engine(sheets)
    recs = engine.recommend_products("biz_001", "cust_1")

    assert len(recs) == 1
    assert recs[0].product_id == "prod_003"  # the other "shirt" product


def test_recommend_products_never_recommends_already_ordered_product():
    sheets = _sheets()
    sheets["ORDERS"] = [
        {
            "order_id": "ord_1",
            "business_id": "biz_001",
            "customer_id": "cust_1",
            "product_id": "prod_001",
            "product_name": "Black Shirt",
            "quantity": "1",
            "unit_price": "1200",
            "total_price": "1200",
            "currency": "BDT",
            "status": "completed",
            "created_at": "2026-01-01T00:00:00+00:00",
        }
    ]
    engine, _ = _engine(sheets)
    recs = engine.recommend_products("biz_001", "cust_1")
    assert all(p.product_id != "prod_001" for p in recs)


def test_recommend_products_uses_conversation_memory_when_no_orders():
    sheets = _sheets()
    sheets["CONVERSATIONS"] = [
        {
            "business_id": "biz_001",
            "customer_id": "cust_browsing",
            "last_intent": "price_inquiry",
            "last_color": "black",
            "last_size": "",
            "last_keywords": "shirt",
            "unresolved_count": "0",
            "human_required": "FALSE",
            "human_required_reason": "",
            "updated_at": "2026-01-01T00:00:00+00:00",
        }
    ]
    engine, _ = _engine(sheets)
    recs = engine.recommend_products("biz_001", "cust_browsing")
    product_ids = {p.product_id for p in recs}
    assert product_ids == {"prod_001", "prod_003"}


def test_recommend_products_returns_empty_with_no_signal():
    engine, _ = _engine()
    assert engine.recommend_products("biz_001", "cust_unknown") == []


def test_upsell_suggests_same_category_higher_priced_first():
    engine, _ = _engine()
    results = engine.suggest_upsell("biz_001", "prod_001")

    assert len(results) == 1
    assert results[0].product_id == "prod_003"
    assert results[0].price == "1500"


def test_upsell_never_recommends_the_same_product():
    engine, _ = _engine()
    results = engine.suggest_upsell("biz_001", "prod_001")
    assert all(p.product_id != "prod_001" for p in results)


def test_upsell_disabled_via_business_rule_returns_empty():
    sheets = _sheets()
    sheets["BUSINESS_RULES"].append(
        {
            "rule_id": "rule_020",
            "business_id": "biz_001",
            "rule_name": "upsell_enabled",
            "rule_value": "FALSE",
            "priority": "1",
            "active": "TRUE",
            "updated_at": "2026-01-01",
        }
    )
    engine, _ = _engine(sheets)
    assert engine.suggest_upsell("biz_001", "prod_001") == []


def test_upsell_never_crosses_business_boundary():
    """prod_001 (biz_001) must never pull in a same-category product that
    actually belongs to a different business."""
    sheets = _sheets()
    sheets["PRODUCTS"].append(
        {
            "product_id": "prod_999",
            "business_id": "biz_002",
            "product_name": "Other Biz Shirt",
            "description": "",
            "category": "shirt",
            "price": "9999",
            "currency": "BDT",
            "stock": "1",
            "stock_status": "in_stock",
            "size": "L",
            "color": "blue",
            "variant": "",
            "sku": "SKU-999",
            "image_url": "",
            "delivery_available": "TRUE",
            "active": "TRUE",
            "updated_at": "2026-01-01",
        }
    )
    engine, _ = _engine(sheets)
    results = engine.suggest_upsell("biz_001", "prod_001")
    assert all(p.product_id != "prod_999" for p in results)


def test_segment_customers_classifies_new_repeat_vip():
    sheets = _sheets()

    def make_order(order_id, customer_id):
        return {
            "order_id": order_id,
            "business_id": "biz_001",
            "customer_id": customer_id,
            "product_id": "prod_001",
            "product_name": "Black Shirt",
            "quantity": "1",
            "unit_price": "1200",
            "total_price": "1200",
            "currency": "BDT",
            "status": "completed",
            "created_at": "2026-01-01T00:00:00+00:00",
        }

    orders = [make_order("ord_new_1", "cust_new")]
    orders += [make_order(f"ord_repeat_{i}", "cust_repeat") for i in range(2)]
    orders += [make_order(f"ord_vip_{i}", "cust_vip") for i in range(5)]
    sheets["ORDERS"] = orders

    engine, _ = _engine(sheets)
    segments = {s.customer_id: s.segment for s in engine.segment_customers("biz_001")}

    assert segments["cust_new"] == "new"
    assert segments["cust_repeat"] == "repeat"
    assert segments["cust_vip"] == "vip"


def test_follow_up_message_none_when_disabled():
    sheets = _sheets()
    sheets["BUSINESS_RULES"].append(
        {
            "rule_id": "rule_030",
            "business_id": "biz_001",
            "rule_name": "follow_up_enabled",
            "rule_value": "FALSE",
            "priority": "1",
            "active": "TRUE",
            "updated_at": "2026-01-01",
        }
    )
    engine, _ = _engine(sheets)
    assert engine.build_follow_up_message("biz_001", "cust_1") is None


def test_follow_up_message_present_when_enabled():
    engine, _ = _engine()
    message = engine.build_follow_up_message("biz_001", "cust_1")
    assert message is not None
    assert len(message) > 0
