from app import create_app


def test_dashboard_services_missing_business_id():
    app = create_app()
    client = app.test_client()
    resp = client.get("/dashboard/services")
    assert resp.status_code == 400


def test_dashboard_services_lists_services_for_business():
    app = create_app()
    client = app.test_client()

    resp = client.get("/dashboard/services", query_string={"business_id": "biz_002"})
    assert resp.status_code == 200
    body = resp.get_json()
    names = {s["service_name"] for s in body["services"]}
    assert "Skin Fade Haircut" in names
    assert body["count"] == 1


def test_dashboard_services_business_isolation():
    app = create_app()
    client = app.test_client()

    resp = client.get("/dashboard/services", query_string={"business_id": "biz_001"})
    body = resp.get_json()
    # biz_001 is a clothing shop — must never see biz_002's salon services.
    names = {s["service_name"] for s in body["services"]}
    assert "Skin Fade Haircut" not in names


def test_dashboard_services_active_only_filter():
    app = create_app()
    client = app.test_client()

    resp = client.get(
        "/dashboard/services",
        query_string={"business_id": "biz_002", "active_only": "true"},
    )
    assert resp.status_code == 200
    for service in resp.get_json()["services"]:
        assert service["active"].upper() == "TRUE"
