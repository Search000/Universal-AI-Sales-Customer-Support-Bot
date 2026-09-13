"""
Language / Intent Engine (Phase 4).

GLOBAL language knowledge only (master rule #2 / #5A): this module may
understand Bangla, English, Banglish, and common typos well enough to pick
an intent and candidate entities. It NEVER decides whether a product,
price, or policy actually exists — that is always verified against
business data by the knowledge engine.
"""
import difflib
import re
from dataclasses import dataclass, field
from typing import Dict, List, Optional

# ---- Global vocabulary (shared across all businesses) ---------------------

COLOR_SYNONYMS: Dict[str, str] = {
    "black": "black", "kalo": "black", "কালো": "black", "কালা": "black", "কালোটা": "black",
    "white": "white", "sada": "white", "সাদা": "white",
    "red": "red", "lal": "red", "লাল": "red",
    "blue": "blue", "nil": "blue", "নীল": "blue",
    "green": "green", "sobuj": "green", "সবুজ": "green",
    "yellow": "yellow", "holud": "yellow", "হলুদ": "yellow",
    "grey": "grey", "gray": "grey", "ash": "grey", "ছাই": "grey",
    "brown": "brown", "bhura": "brown", "বাদামি": "brown",
    "pink": "pink", "গোলাপি": "pink",
    "purple": "purple", "বেগুনি": "purple",
    "orange": "orange", "কমলা": "orange",
}

SIZE_TOKENS = {"xs", "s", "m", "l", "xl", "xxl", "xxxl", "3xl", "freesize"}

PRICE_KEYWORDS = ["price", "dam", "daam", "কত", "দাম", "koto", "কত টাকা", "দাম কত", "cost", "rate"]

AVAILABILITY_KEYWORDS = ["available", "ache", "আছে", "stock", "পাওয়া যাবে", "pawa jabe", "in stock"]

GREETING_KEYWORDS = ["assalamualaikum", "আসসালামু", "hello", "hi ", "হাই", "হ্যালো"]

POLICY_KEYWORDS: Dict[str, List[str]] = {
    "return": ["return", "ফেরত"],
    "exchange": ["exchange", "বদল"],
    "refund": ["refund", "রিফান্ড"],
    "delivery": ["delivery", "ডেলিভারি", "koto din", "কত দিন"],
    "warranty": ["warranty", "ওয়ারেন্টি", "guarantee", "গ্যারান্টি"],
}

# Words that should never be treated as a candidate product keyword.
STOPWORDS = set(
    PRICE_KEYWORDS
    + AVAILABILITY_KEYWORDS
    + GREETING_KEYWORDS
    + list(COLOR_SYNONYMS.keys())
    + list(SIZE_TOKENS)
    + [
        "vai", "ভাই", "আমার", "আমি", "লাগবে", "চাই", "na", "না", "ki", "কি",
        "er", "ta", "টা", "the", "a", "an", "is", "for", "please", "plz",
    ]
)


@dataclass
class IntentResult:
    intent: str
    confidence: float
    meta: Optional[Dict] = None


@dataclass
class Entities:
    color: Optional[str] = None
    size: Optional[str] = None
    keywords: List[str] = field(default_factory=list)


def _tokenize(text: str) -> List[str]:
    return re.findall(r"[\w\u0980-\u09FF]+", text.lower())


def _contains_any(text: str, keywords: List[str]) -> bool:
    return any(kw in text for kw in keywords)


def _fuzzy_token_hits(tokens: List[str], vocab: List[str], cutoff: float = 0.82) -> bool:
    """Typo tolerance: e.g. 'pric' still matches 'price'."""
    for token in tokens:
        if difflib.get_close_matches(token, vocab, n=1, cutoff=cutoff):
            return True
    return False


def detect_intent(message: str) -> IntentResult:
    text = message.lower().strip()
    tokens = _tokenize(text)

    if _contains_any(text, GREETING_KEYWORDS):
        return IntentResult("GREETING", 0.9)

    for policy_type, kws in POLICY_KEYWORDS.items():
        if _contains_any(text, kws):
            return IntentResult("POLICY_INQUIRY", 0.85, meta={"policy_type": policy_type})

    if _contains_any(text, PRICE_KEYWORDS) or _fuzzy_token_hits(tokens, PRICE_KEYWORDS):
        return IntentResult("PRICE_INQUIRY", 0.8)

    if _contains_any(text, AVAILABILITY_KEYWORDS) or _fuzzy_token_hits(tokens, AVAILABILITY_KEYWORDS):
        return IntentResult("AVAILABILITY_INQUIRY", 0.8)

    if tokens:
        return IntentResult("PRODUCT_SEARCH", 0.5)

    return IntentResult("UNKNOWN", 0.0)


def extract_entities(message: str) -> Entities:
    tokens = _tokenize(message)

    color = None
    for token in tokens:
        if token in COLOR_SYNONYMS:
            color = COLOR_SYNONYMS[token]
            continue  # keep scanning — last mentioned color wins (handles "not X but Y")
        fuzzy = difflib.get_close_matches(token, list(COLOR_SYNONYMS.keys()), n=1, cutoff=0.82)
        if fuzzy:
            color = COLOR_SYNONYMS[fuzzy[0]]

    size = None
    for token in tokens:
        if token in SIZE_TOKENS:
            size = token.upper()
            break

    keywords = [t for t in tokens if t not in STOPWORDS and len(t) > 1]

    return Entities(color=color, size=size, keywords=keywords)
