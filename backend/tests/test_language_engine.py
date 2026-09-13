from app.services.language_engine import detect_intent, extract_entities


# ---- intent detection --------------------------------------------------
def test_price_intent_english():
    result = detect_intent("what is the price of this shirt")
    assert result.intent == "PRICE_INQUIRY"


def test_price_intent_bangla():
    result = detect_intent("দাম কত?")
    assert result.intent == "PRICE_INQUIRY"


def test_price_intent_banglish():
    result = detect_intent("shirt ta koto?")
    assert result.intent == "PRICE_INQUIRY"


def test_price_intent_typo_tolerance():
    # "pric" instead of "price" — typo handling
    result = detect_intent("pric koto")
    assert result.intent == "PRICE_INQUIRY"


def test_availability_intent_bangla():
    result = detect_intent("black shirt XL আছে?")
    assert result.intent == "AVAILABILITY_INQUIRY"


def test_policy_intent_return():
    result = detect_intent("return policy ki?")
    assert result.intent == "POLICY_INQUIRY"
    assert result.meta["policy_type"] == "return"


def test_greeting_intent():
    result = detect_intent("Assalamualaikum")
    assert result.intent == "GREETING"


# ---- Phase 9: human handover intent -------------------------------------
def test_human_request_keyword_detected():
    result = detect_intent("ভাই কাউকে দেন")
    assert result.intent == "HUMAN_HANDOVER"
    assert result.meta["reason"] == "human_request"


def test_human_request_english():
    result = detect_intent("I want to talk to a human agent")
    assert result.intent == "HUMAN_HANDOVER"
    assert result.meta["reason"] == "human_request"


def test_angry_customer_keyword_detected():
    result = detect_intent("আপনাদের সার্ভিস খারাপ, refund দেন এখনি")
    assert result.intent == "HUMAN_HANDOVER"
    assert result.meta["reason"] == "angry_customer"


def test_human_handover_takes_priority_over_greeting():
    result = detect_intent("hello, কাউকে দেন")
    assert result.intent == "HUMAN_HANDOVER"


def test_unknown_intent_for_gibberish():
    result = detect_intent("   ")
    assert result.intent == "UNKNOWN"


# ---- entity extraction ---------------------------------------------------
def test_extract_color_bangla():
    entities = extract_entities("লাল শার্ট আছে?")
    assert entities.color == "red"


def test_extract_color_english():
    entities = extract_entities("black shirt XL ache?")
    assert entities.color == "black"
    assert entities.size == "XL".lower().upper()  # "XL"


def test_extract_color_typo_tolerance():
    # "blak" instead of "black"
    entities = extract_entities("blak shirt ache?")
    assert entities.color == "black"


def test_last_mentioned_color_wins():
    """'red না black চাই' — customer says not red but black — last one wins."""
    entities = extract_entities("লাল na কালো লাগবে")
    assert entities.color == "black"


def test_keywords_exclude_stopwords():
    entities = extract_entities("black shirt ache?")
    assert "shirt" in entities.keywords
    assert "black" not in entities.keywords
    assert "ache" not in entities.keywords
