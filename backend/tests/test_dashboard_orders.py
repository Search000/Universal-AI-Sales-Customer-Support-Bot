from app import create_app
from app.services import engine_factory


def test_dashboard_orders_missing_business_id():
    app = create_app()
    client = app.test_client()
    resp = client.get("/dashboard/orders")
    assert resp.status_code == 400


def test_dashboard_orders_lists_orders_for_business():
    app = create_app()
    client = app.test_client()

    pipeline = engine_factory.get_message_pipeline()
    result = pipeline._order_engine.place_order(
        "biz_001", "dash_order_customer", "prod_001", quantity=1
    )
    assert result.error is None

    resp = client.get("/dashboard/orders", query_string={"business_id": "biz_001"})
    assert resp.status_code == 200
    body = resp.get_json()
    order_ids = {o["order_id"] for o in body["orders"]}
    assert result.order.order_id in order_ids


def test_dashboard_orders_business_isolation():
    app = create_app()
    client = app.test_client()

    pipeline = engine_factory.get_message_pipeline()
    result = pipeline._order_engine.place_order(
        "biz_001", "isolation_order_customer", "prod_001", quantity=1
    )
    assert result.error is None

    resp_wrong_biz = client.get("/dashboard/orders", query_string={"business_id": "biz_002"})
    order_ids = {o["order_id"] for o in resp_wrong_biz.get_json()["orders"]}
    assert result.order.order_id not in order_ids


def test_dashboard_orders_status_filter():
    app = create_app()
    client = app.test_client()

    pipeline = engine_factory.get_message_pipeline()
    pipeline._order_engine.place_order(
        "biz_001", "status_filter_customer", "prod_001", quantity=1
    )

    resp = client.get(
        "/dashboard/orders",
        query_string={"business_id": "biz_001", "status": "pending"},
    )
    assert resp.status_code == 200
    for order in resp.get_json()["orders"]:
        assert order["status"] == "pending"
