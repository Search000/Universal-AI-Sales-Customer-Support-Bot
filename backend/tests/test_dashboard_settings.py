from app import create_app


def test_dashboard_settings_get_missing_business_id():
    app = create_app()
    client = app.test_client()
    resp = client.get("/dashboard/settings")
    assert resp.status_code == 400


def test_dashboard_settings_get_not_found():
    app = create_app()
    client = app.test_client()
    resp = client.get("/dashboard/settings", query_string={"business_id": "biz_does_not_exist"})
    assert resp.status_code == 404


def test_dashboard_settings_get_returns_current_values():
    app = create_app()
    client = app.test_client()
    resp = client.get("/dashboard/settings", query_string={"business_id": "biz_001"})
    assert resp.status_code == 200
    body = resp.get_json()["settings"]
    assert body["business_id"] == "biz_001"
    assert body["business_name"] == "Rupa Fashion"


def test_dashboard_settings_update_editable_field():
    app = create_app()
    client = app.test_client()

    resp = client.post(
        "/dashboard/settings",
        json={"business_id": "biz_001", "opening_hours": "11am-10pm"},
    )
    assert resp.status_code == 200
    body = resp.get_json()
    assert "opening_hours" in body["updated_fields"]
    assert body["settings"]["opening_hours"] == "11am-10pm"

    # Persisted — a fresh GET shows the change.
    resp2 = client.get("/dashboard/settings", query_string={"business_id": "biz_001"})
    assert resp2.get_json()["settings"]["opening_hours"] == "11am-10pm"


def test_dashboard_settings_cannot_change_business_id():
    app = create_app()
    client = app.test_client()

    resp = client.post(
        "/dashboard/settings",
        json={"business_id": "biz_001", "created_at": "hacked", "address": "New Address"},
    )
    body = resp.get_json()
    # business_id/created_at are identity fields, never in the editable set.
    assert "business_id" not in body["updated_fields"]
    assert "created_at" not in body["updated_fields"]
    assert "address" in body["updated_fields"]
    assert body["settings"]["business_id"] == "biz_001"


def test_dashboard_settings_missing_business_id_on_post():
    app = create_app()
    client = app.test_client()
    resp = client.post("/dashboard/settings", json={"opening_hours": "9am-5pm"})
    assert resp.status_code == 400
