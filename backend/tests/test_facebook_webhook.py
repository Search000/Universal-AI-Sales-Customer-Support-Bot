import hashlib
import hmac
import json

from app import create_app
from app.config import config
from app.integrations.facebook.client import verify_signature
from app.services import engine_factory


def _sign(secret: str, body: bytes) -> str:
    return "sha256=" + hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()


def test_verify_signature_valid():
    body = b'{"a": 1}'
    sig = _sign("mysecret", body)
    assert verify_signature("mysecret", body, sig) is True


def test_verify_signature_invalid():
    body = b'{"a": 1}'
    sig = _sign("wrongsecret", body)
    assert verify_signature("mysecret", body, sig) is False


def test_verify_signature_missing_header():
    assert verify_signature("mysecret", b"{}", "") is False


def test_webhook_get_verify_success(monkeypatch):
    monkeypatch.setattr(config, "META_VERIFY_TOKEN", "my_verify_token")
    app = create_app()
    client = app.test_client()
    resp = client.get(
        "/webhooks/facebook",
        query_string={
            "hub.mode": "subscribe",
            "hub.verify_token": "my_verify_token",
            "hub.challenge": "12345",
        },
    )
    assert resp.status_code == 200
    assert resp.data.decode() == "12345"


def test_webhook_get_verify_wrong_token(monkeypatch):
    monkeypatch.setattr(config, "META_VERIFY_TOKEN", "my_verify_token")
    app = create_app()
    client = app.test_client()
    resp = client.get(
        "/webhooks/facebook",
        query_string={
            "hub.mode": "subscribe",
            "hub.verify_token": "wrong",
            "hub.challenge": "12345",
        },
    )
    assert resp.status_code == 403


def test_webhook_post_rejects_bad_signature(monkeypatch):
    monkeypatch.setattr(config, "META_APP_SECRET", "appsecret")
    app = create_app()
    client = app.test_client()
    body = json.dumps({"object": "page", "entry": []}).encode()
    resp = client.post(
        "/webhooks/facebook",
        data=body,
        content_type="application/json",
        headers={"X-Hub-Signature-256": "sha256=deadbeef"},
    )
    assert resp.status_code == 403


def test_webhook_post_unknown_page_dropped(monkeypatch):
    monkeypatch.setattr(config, "META_APP_SECRET", "")
    app = create_app()
    client = app.test_client()
    payload = {
        "object": "page",
        "entry": [
            {
                "id": "page_not_configured",
                "messaging": [
                    {
                        "sender": {"id": "customer_1"},
                        "message": {"text": "hi"},
                    }
                ],
            }
        ],
    }
    resp = client.post("/webhooks/facebook", json=payload)
    assert resp.status_code == 200
    assert resp.get_json()["status"] == "EVENT_RECEIVED"


def test_webhook_post_happy_path_sends_reply(monkeypatch):
    monkeypatch.setattr(config, "META_APP_SECRET", "")
    app = create_app()
    client = app.test_client()

    fb_client = engine_factory.get_facebook_client()
    before_count = len(fb_client.sent_messages)

    payload = {
        "object": "page",
        "entry": [
            {
                "id": "page_test_001",  # matches biz_001 in sample data
                "messaging": [
                    {
                        "sender": {"id": "customer_42"},
                        "message": {"text": "price koto?"},
                    }
                ],
            }
        ],
    }
    resp = client.post("/webhooks/facebook", json=payload)
    assert resp.status_code == 200

    assert len(fb_client.sent_messages) == before_count + 1
    sent = fb_client.sent_messages[-1]
    assert sent["recipient_id"] == "customer_42"
    assert isinstance(sent["text"], str) and len(sent["text"]) > 0
