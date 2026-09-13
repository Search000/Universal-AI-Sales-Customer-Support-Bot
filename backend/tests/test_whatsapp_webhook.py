import hashlib
import hmac
import json

from app import create_app
from app.config import config
from app.services import engine_factory


def _sign(secret: str, body: bytes) -> str:
    return "sha256=" + hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()


def test_whatsapp_webhook_get_verify_success(monkeypatch):
    monkeypatch.setattr(config, "META_VERIFY_TOKEN", "my_verify_token")
    app = create_app()
    client = app.test_client()
    resp = client.get(
        "/webhooks/whatsapp",
        query_string={
            "hub.mode": "subscribe",
            "hub.verify_token": "my_verify_token",
            "hub.challenge": "98765",
        },
    )
    assert resp.status_code == 200
    assert resp.data.decode() == "98765"


def test_whatsapp_webhook_get_verify_wrong_token(monkeypatch):
    monkeypatch.setattr(config, "META_VERIFY_TOKEN", "my_verify_token")
    app = create_app()
    client = app.test_client()
    resp = client.get(
        "/webhooks/whatsapp",
        query_string={
            "hub.mode": "subscribe",
            "hub.verify_token": "wrong",
            "hub.challenge": "98765",
        },
    )
    assert resp.status_code == 403


def test_whatsapp_webhook_post_rejects_bad_signature(monkeypatch):
    monkeypatch.setattr(config, "META_APP_SECRET", "appsecret")
    app = create_app()
    client = app.test_client()
    body = json.dumps({"object": "whatsapp_business_account", "entry": []}).encode()
    resp = client.post(
        "/webhooks/whatsapp",
        data=body,
        content_type="application/json",
        headers={"X-Hub-Signature-256": "sha256=deadbeef"},
    )
    assert resp.status_code == 403


def test_whatsapp_webhook_post_unknown_number_dropped(monkeypatch):
    monkeypatch.setattr(config, "META_APP_SECRET", "")
    app = create_app()
    client = app.test_client()
    payload = {
        "object": "whatsapp_business_account",
        "entry": [
            {
                "id": "waba_1",
                "changes": [
                    {
                        "field": "messages",
                        "value": {
                            "metadata": {"phone_number_id": "not_configured"},
                            "messages": [
                                {"from": "8801000000001", "text": {"body": "hi"}}
                            ],
                        },
                    }
                ],
            }
        ],
    }
    resp = client.post("/webhooks/whatsapp", json=payload)
    assert resp.status_code == 200
    assert resp.get_json()["status"] == "EVENT_RECEIVED"


def test_whatsapp_webhook_post_happy_path_sends_reply(monkeypatch):
    monkeypatch.setattr(config, "META_APP_SECRET", "")
    app = create_app()
    client = app.test_client()

    wa_client = engine_factory.get_whatsapp_client()
    before_count = len(wa_client.sent_messages)

    payload = {
        "object": "whatsapp_business_account",
        "entry": [
            {
                "id": "waba_1",
                "changes": [
                    {
                        "field": "messages",
                        "value": {
                            "metadata": {"phone_number_id": "wa_test_002"},  # biz_002
                            "messages": [
                                {
                                    "from": "8801000000042",
                                    "text": {"body": "fade koto?"},
                                }
                            ],
                        },
                    }
                ],
            }
        ],
    }
    resp = client.post("/webhooks/whatsapp", json=payload)
    assert resp.status_code == 200

    assert len(wa_client.sent_messages) == before_count + 1
    sent = wa_client.sent_messages[-1]
    assert sent["to"] == "8801000000042"
    assert sent["phone_number_id"] == "wa_test_002"
    assert isinstance(sent["text"], str) and len(sent["text"]) > 0
