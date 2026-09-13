from app import create_app
from app.services import engine_factory


def test_config_requires_business_id():
    app = create_app()
    client = app.test_client()
    resp = client.get("/follow-up/config")
    assert resp.status_code == 400


def test_config_returns_defaults():
    app = create_app()
    client = app.test_client()
    resp = client.get("/follow-up/config", query_string={"business_id": "biz_001"})
    assert resp.status_code == 200
    assert resp.get_json()["config"]["follow_up_enabled"] == "TRUE"


def test_abandoned_conversations_empty_for_fresh_business():
    app = create_app()
    client = app.test_client()
    resp = client.get(
        "/follow-up/abandoned-conversations", query_string={"business_id": "biz_001"}
    )
    assert resp.status_code == 200
    assert resp.get_json()["count"] == 0


def test_abandoned_orders_requires_business_id():
    app = create_app()
    client = app.test_client()
    resp = client.get("/follow-up/abandoned-orders")
    assert resp.status_code == 400


def test_recommendations_requires_customer_id():
    app = create_app()
    client = app.test_client()
    resp = client.get("/follow-up/recommendations", query_string={"business_id": "biz_001"})
    assert resp.status_code == 400


def test_recommendations_after_a_real_order():
    app = create_app()
    client = app.test_client()

    pipeline = engine_factory.get_message_pipeline()
    result = pipeline._order_engine.place_order("biz_001", "cust_route_test", "prod_001", quantity=1)
    assert result.error is None

    resp = client.get(
        "/follow-up/recommendations",
        query_string={"business_id": "biz_001", "customer_id": "cust_route_test"},
    )
    assert resp.status_code == 200
    body = resp.get_json()
    # prod_001 (shirt, ordered) should never be recommended back to itself.
    assert all(p["product_id"] != "prod_001" for p in body["recommendations"])


def test_upsell_requires_product_id():
    app = create_app()
    client = app.test_client()
    resp = client.get("/follow-up/upsell", query_string={"business_id": "biz_001"})
    assert resp.status_code == 400


def test_upsell_business_isolation_via_route():
    app = create_app()
    client = app.test_client()
    # prod_001 belongs to biz_001 — asking under biz_002 must find nothing
    # because biz_002 has no such product in its own catalog.
    resp = client.get(
        "/follow-up/upsell",
        query_string={"business_id": "biz_002", "product_id": "prod_001"},
    )
    assert resp.status_code == 200
    assert resp.get_json()["count"] == 0


def test_segments_endpoint_returns_list():
    app = create_app()
    client = app.test_client()
    resp = client.get("/follow-up/segments", query_string={"business_id": "biz_001"})
    assert resp.status_code == 200
    assert "segments" in resp.get_json()


def test_follow_up_message_requires_customer_id():
    app = create_app()
    client = app.test_client()
    resp = client.get("/follow-up/message", query_string={"business_id": "biz_001"})
    assert resp.status_code == 400


def test_follow_up_message_returned_for_valid_request():
    app = create_app()
    client = app.test_client()
    resp = client.get(
        "/follow-up/message",
        query_string={"business_id": "biz_001", "customer_id": "cust_1"},
    )
    assert resp.status_code == 200
    assert resp.get_json()["enabled"] is True
