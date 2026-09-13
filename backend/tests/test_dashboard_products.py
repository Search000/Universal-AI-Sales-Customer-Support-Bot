from app import create_app


def test_dashboard_products_missing_business_id():
    app = create_app()
    client = app.test_client()
    resp = client.get("/dashboard/products")
    assert resp.status_code == 400


def test_dashboard_products_lists_products_for_business():
    app = create_app()
    client = app.test_client()

    resp = client.get("/dashboard/products", query_string={"business_id": "biz_001"})
    assert resp.status_code == 200
    body = resp.get_json()
    names = {p["product_name"] for p in body["products"]}
    assert "Black Shirt" in names
    assert "Red Panjabi" in names
    assert body["count"] == 2


def test_dashboard_products_business_isolation():
    app = create_app()
    client = app.test_client()

    resp = client.get("/dashboard/products", query_string={"business_id": "biz_002"})
    body = resp.get_json()
    names = {p["product_name"] for p in body["products"]}
    # biz_002 is a salon — must never see biz_001's clothing products.
    assert "Black Shirt" not in names
    assert "Red Panjabi" not in names


def test_dashboard_products_active_only_filter():
    app = create_app()
    client = app.test_client()

    resp = client.get(
        "/dashboard/products",
        query_string={"business_id": "biz_001", "active_only": "true"},
    )
    assert resp.status_code == 200
    for product in resp.get_json()["products"]:
        assert product["active"].upper() == "TRUE"
