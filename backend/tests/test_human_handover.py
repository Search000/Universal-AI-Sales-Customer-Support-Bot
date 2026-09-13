from app.services.human_handover import evaluate


def test_explicit_human_handover_intent_always_required():
    decision = evaluate(intent="HUMAN_HANDOVER", intent_meta={"reason": "human_request"})
    assert decision.required is True
    assert decision.reason == "human_request"


def test_angry_reason_is_preserved():
    decision = evaluate(intent="HUMAN_HANDOVER", intent_meta={"reason": "angry_customer"})
    assert decision.required is True
    assert decision.reason == "angry_customer"


def test_unsupported_request_triggers_handover():
    decision = evaluate(intent="ORDER_INTENT", unsupported=True)
    assert decision.required is True
    assert decision.reason == "unsupported_request"


def test_data_unavailable_triggers_handover_immediately():
    decision = evaluate(intent="PRICE_INQUIRY", data_unavailable=True, unresolved_count=1)
    assert decision.required is True
    assert decision.reason == "business_data_unavailable"


def test_single_unresolved_turn_does_not_trigger_handover():
    decision = evaluate(intent="PRODUCT_SEARCH", unresolved_count=1)
    assert decision.required is False


def test_repeated_unresolved_turns_trigger_handover():
    decision = evaluate(intent="PRODUCT_SEARCH", unresolved_count=2)
    assert decision.required is True
    assert decision.reason == "repeated_misunderstanding"


def test_normal_resolved_message_does_not_trigger_handover():
    decision = evaluate(intent="PRICE_INQUIRY", unresolved_count=0)
    assert decision.required is False
    assert decision.reason is None
