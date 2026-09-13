from app import create_app


def test_onboarding_page_loads():
    app = create_app()
    client = app.test_client()
    resp = client.get("/dashboard/onboard")
    assert resp.status_code == 200
    assert b"Business Toiri Koro" in resp.data
    assert b"/dashboard/businesses" in resp.data
