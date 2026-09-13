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

# Words that mark a nearby number as an actual item quantity, not some
# other number in the message (phone number, address, price, etc).
QUANTITY_UNIT_WORDS = {
    "ta", "টা", "টি", "pc", "pcs", "piece", "pieces", "qty", "quantity",
    "copy", "কপি", "set", "সেট",
}

# A quantity a customer would realistically type by hand. Anything longer
# (phone numbers are 10-11 digits, addresses/postal codes vary) is almost
# certainly NOT a quantity — see extract_entities().
_MAX_PLAUSIBLE_QUANTITY_DIGITS = 3

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

ORDER_KEYWORDS = [
    "order", "অর্ডার", "kinbo", "কিনবো", "কিনব", "nibo", "নিবো", "নিব",
    "confirm", "কনফার্ম", "নিতে চাই", "kinte chai", "নিতে চাচ্ছি",
    "order korte chai", "অর্ডার করতে চাই", "book", "বুক",
]

# Phase 9: explicit request to talk to a human, or clear signs the customer
# is angry/upset. Checked with highest priority — if a customer is asking
# for a person or is clearly upset, no other intent guess matters more.
HUMAN_REQUEST_KEYWORDS = [
    "human", "real person", "agent", "manager", "owner",
    "মানুষ", "মানুষের সাথে", "কাউকে দেন", "এজেন্ট", "ম্যানেজার",
    "owner এর সাথে", "ওনার সাথে কথা", "কথা বলিয়ে দেন", "কথা বলতে চাই",
]

ANGRY_KEYWORDS = [
    "worst service", "bad service", "scam", "cheater", "fraud",
    "সার্ভিস খারাপ", "খারাপ সার্ভিস", "বাজে সার্ভিস", "প্রতারণা",
    "চিটার", "ফালতু", "রিফান্ড দেন", "refund দেন এখনি", "complain",
    "অভিযোগ",
]

# Words that should never be treated as a candidate product keyword.
STOPWORDS = set(
    PRICE_KEYWORDS
    + AVAILABILITY_KEYWORDS
    + GREETING_KEYWORDS
    + ORDER_KEYWORDS
    + HUMAN_REQUEST_KEYWORDS
    + ANGRY_KEYWORDS
    + list(COLOR_SYNONYMS.keys())
    + list(SIZE_TOKENS)
    + [
        "vai", "ভাই", "আমার", "আমি", "লাগবে", "চাই", "na", "না", "ki", "কি",
        "chai", "chao", "chan", "korte", "korbo", "koro", "lagbe", "নিতে",
        "নিব", "নিবো", "কিনব", "কিনবো",
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
    quantity: Optional[int] = None


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

    if _contains_any(text, ANGRY_KEYWORDS):
        return IntentResult("HUMAN_HANDOVER", 0.95, meta={"reason": "angry_customer"})

    if _contains_any(text, HUMAN_REQUEST_KEYWORDS):
        return IntentResult("HUMAN_HANDOVER", 0.95, meta={"reason": "human_request"})

    if _contains_any(text, GREETING_KEYWORDS):
        return IntentResult("GREETING", 0.9)

    for policy_type, kws in POLICY_KEYWORDS.items():
        if _contains_any(text, kws):
            return IntentResult("POLICY_INQUIRY", 0.85, meta={"policy_type": policy_type})

    if _contains_any(text, ORDER_KEYWORDS) or _fuzzy_token_hits(tokens, ORDER_KEYWORDS):
        return IntentResult("ORDER_INTENT", 0.85)

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

    keywords = [t for t in tokens if t not in STOPWORDS and len(t) > 1 and not t.isdigit()]

    # Quantity: a message can contain several unrelated numbers (a phone
    # number, an address, a price) — naively taking "the first digit
    # token" misreads a phone number as the order quantity (e.g. "amar
    # phone 01711111111" -> quantity=1711111111), which then wrongly
    # fails the order as "out of stock". Prefer a digit token sitting
    # right next to a quantity word ("2 ta", "৩ pcs"); only fall back to
    # a bare number if it's short enough to plausibly BE a quantity —
    # never a long run of digits like a phone number or postal code.
    quantity = None
    for i, token in enumerate(tokens):
        if not token.isdigit():
            continue
        neighbors = tokens[max(0, i - 1):i] + tokens[i + 1:i + 2]
        if any(n in QUANTITY_UNIT_WORDS for n in neighbors):
            quantity = int(token)
            break
    if quantity is None:
        for token in tokens:
            if token.isdigit() and len(token) <= _MAX_PLAUSIBLE_QUANTITY_DIGITS:
                quantity = int(token)
                break

    return Entities(color=color, size=size, keywords=keywords, quantity=quantity)
