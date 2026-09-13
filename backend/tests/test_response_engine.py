import pytest

from app.integrations.gemini.fake_client import FakeGeminiClient
from app.services.response_engine import generate_final_response


def test_no_client_returns_draft_response_unchanged():
    result = generate_final_response(
        client=None,
        business_name="Test Shop",
        customer_message="black shirt price koto?",
        intent="PRICE_INQUIRY",
        retrieved_data={"products": [{"product_name": "Black Shirt"}]},
        draft_response="Black Shirt price 1200 taka.",
    )
    assert result == "Black Shirt price 1200 taka."


def test_no_retrieved_data_skips_ai_even_with_client():
    client = FakeGeminiClient(canned_response="should never be used")
    result = generate_final_response(
        client=client,
        business_name="Test Shop",
        customer_message="return policy ki?",
        intent="POLICY_INQUIRY",
        retrieved_data=None,
        draft_response="এই তথ্যটি আমার current business data-তে নেই।",
    )
    assert result == "এই তথ্যটি আমার current business data-তে নেই।"
    assert client.last_prompt is None  # never called


def test_grounded_data_uses_ai_phrasing():
    client = FakeGeminiClient(canned_response="Black Shirt ta 1200 taka, nice choice!")
    result = generate_final_response(
        client=client,
        business_name="Test Shop",
        customer_message="black shirt price koto?",
        intent="PRICE_INQUIRY",
        retrieved_data={"products": [{"product_name": "Black Shirt", "price": 1200}]},
        draft_response="Black Shirt price 1200 taka.",
    )
    assert result == "Black Shirt ta 1200 taka, nice choice!"
    assert "1200" in client.last_prompt  # retrieved data was actually passed in


def test_ai_failure_falls_back_to_draft_response():
    class BrokenClient:
        def generate(self, prompt: str) -> str:
            raise RuntimeError("quota exceeded")

    result = generate_final_response(
        client=BrokenClient(),
        business_name="Test Shop",
        customer_message="black shirt price koto?",
        intent="PRICE_INQUIRY",
        retrieved_data={"products": [{"product_name": "Black Shirt"}]},
        draft_response="Black Shirt price 1200 taka.",
    )
    assert result == "Black Shirt price 1200 taka."


def test_empty_ai_response_falls_back_to_draft():
    client = FakeGeminiClient(canned_response="")
    result = generate_final_response(
        client=client,
        business_name="Test Shop",
        customer_message="black shirt price koto?",
        intent="PRICE_INQUIRY",
        retrieved_data={"products": [{"product_name": "Black Shirt"}]},
        draft_response="Black Shirt price 1200 taka.",
    )
    assert result == "Black Shirt price 1200 taka."
