from app import create_app
from app.services import engine_factory


def test_dashboard_analytics_missing_business_id():
    app = create_app()
    client = app.test_client()
    resp = client.get("/dashboard/analytics")
    assert resp.status_code == 400


def test_dashboard_analytics_counts_products_and_services():
    app = create_app()
    client = app.test_client()

    resp = client.get("/dashboard/analytics", query_string={"business_id": "biz_001"})
    assert resp.status_code == 200
    body = resp.get_json()
    assert body["business_id"] == "biz_001"
    assert body["total_products"] == 2  # Black Shirt, Red Panjabi
    assert body["total_services"] == 0  # biz_001 is clothing, no services


def test_dashboard_analytics_reflects_orders_and_revenue():
    app = create_app()
    client = app.test_client()

    pipeline = engine_factory.get_message_pipeline()
    result = pipeline._order_engine.place_order(
        "biz_001", "analytics_customer", "prod_001", quantity=1
    )
    assert result.error is None
    expected_revenue = float(result.order.total_price)

    resp = client.get("/dashboard/analytics", query_string={"business_id": "biz_001"})
    body = resp.get_json()
    assert body["total_orders"] >= 1
    assert body["orders_by_status"].get("pending", 0) >= 1
    assert body["total_revenue"] >= expected_revenue


def test_dashboard_analytics_business_isolation():
    app = create_app()
    client = app.test_client()

    resp = client.get("/dashboard/analytics", query_string={"business_id": "biz_002"})
    body = resp.get_json()
    # biz_002 is the salon — must never see biz_001's product counts.
    assert body["total_products"] == 0
    assert body["total_services"] == 1
