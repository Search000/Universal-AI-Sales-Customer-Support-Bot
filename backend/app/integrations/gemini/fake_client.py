"""
Fake Gemini client — used in tests and local dev when GEMINI_API_KEY is not
set. Never calls any external API. Returns a deterministic, clearly-fake
string so tests can assert on it without network access.
"""


class FakeGeminiClient:
    def __init__(self, canned_response: str = "[FAKE_AI_RESPONSE]"):
        self._canned_response = canned_response
        self.last_prompt: str | None = None

    def generate(self, prompt: str) -> str:
        self.last_prompt = prompt
        return self._canned_response
