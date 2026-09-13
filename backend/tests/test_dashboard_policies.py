from app import create_app


def test_dashboard_policies_missing_business_id():
    app = create_app()
    client = app.test_client()
    resp = client.get("/dashboard/policies")
    assert resp.status_code == 400


def test_dashboard_policies_lists_policies_for_business():
    app = create_app()
    client = app.test_client()

    resp = client.get("/dashboard/policies", query_string={"business_id": "biz_001"})
    assert resp.status_code == 200
    body = resp.get_json()
    types = {p["policy_type"] for p in body["policies"]}
    assert "return" in types
    assert body["count"] == 1


def test_dashboard_policies_business_isolation():
    app = create_app()
    client = app.test_client()

    resp = client.get("/dashboard/policies", query_string={"business_id": "biz_002"})
    body = resp.get_json()
    types = {p["policy_type"] for p in body["policies"]}
    assert "return" not in types


def test_dashboard_policies_active_only_filter():
    app = create_app()
    client = app.test_client()

    resp = client.get(
        "/dashboard/policies",
        query_string={"business_id": "biz_001", "active_only": "true"},
    )
    assert resp.status_code == 200
    for policy in resp.get_json()["policies"]:
        assert policy["active"].upper() == "TRUE"
