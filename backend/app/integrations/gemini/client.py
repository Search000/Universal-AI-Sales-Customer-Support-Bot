"""
Gemini AI client (Phase 5).

Thin wrapper around google-generativeai. Isolated here so:
- No other module imports google.generativeai directly.
- It can be swapped for FakeGeminiClient in tests / when no key is set.
- If Gemini errors out, callers must have a safe fallback (never invent data).
"""
import logging

logger = logging.getLogger(__name__)


class GeminiClient:
    def __init__(self, api_key: str, model_name: str = "gemini-2.0-flash"):
        import google.generativeai as genai

        genai.configure(api_key=api_key)
        self._model = genai.GenerativeModel(model_name)

    def generate(self, prompt: str) -> str:
        """Returns the model's text reply. Raises on failure — caller
        (response_engine) must catch and fall back to the safe template
        response, never leave the customer with an exception."""
        response = self._model.generate_content(prompt)
        return (response.text or "").strip()
