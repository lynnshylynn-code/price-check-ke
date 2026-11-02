from __future__ import annotations

import pytest

from price_check_api import dialogue, trained_assistant
from price_check_api.listings import get_listings
from price_check_api.schemas import MarketQuestionResponse


@pytest.fixture
def known_entities(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(dialogue, "_known_entities", lambda: {
        "store": {"naivas", "quickmart", "carrefour"},
        "other_store": {"naivas", "quickmart", "carrefour"},
        "product": {"milk", "eggs"},
        "group": {"milk", "eggs"}, "category": {"dairy"},
        "county": {"nairobi", "garissa"}, "commodity": {"beans", "maize"},
        "year": {"2023", "2024"},
    })
    monkeypatch.setattr(dialogue, "get_listings", lambda: [])


def _response(
    intent: str = "cheapest_item",
    entities: dict | None = None,
) -> MarketQuestionResponse:
    return MarketQuestionResponse(
        answer="A grounded answer.", source_name="Snapshot", source_url=None,
        coverage_start=None, coverage_end=None, intent=intent, intent_confidence=0.9,
        entities=entities or {},
    )


def test_context_drops_unknown_fields_and_ignores_invalid_values(known_entities) -> None:
    clean = dialogue.validate_context({
        "last_intent": "cheapest_item", "entities": {"product": "milk", "secret": "drop"},
        "last_listing_ids": [], "offset": 0, "pending_slot": None, "turn_count": 2,
        "unexpected": "ignored",
    })
    assert "unexpected" not in clean
    assert "secret" not in clean["entities"]
    assert dialogue.validate_context({"entities": {"store": "unknown shop"}}) == {}
    assert dialogue.validate_context({"context": "x" * dialogue.MAX_CONTEXT_BYTES}) == {}
    assert dialogue.validate_context({"last_listing_ids": ["not-a-listing"]}) == {}


@pytest.mark.parametrize(
    ("question", "expected", "intent"),
    [
        ("and at Quickmart?", "swap_store", "cheapest_item"),
        ("what about eggs?", "swap_product", "cheapest_item"),
        ("and in Garissa?", "swap_county_or_commodity", "market_price"),
        ("and in 2023?", "swap_year", "food_inflation"),
        ("show more", "show_more", "cheapest_item"),
        ("only at Naivas", "refine_store", "cheapest_item"),
        ("why?", "explain", "cheapest_item"),
        ("thanks", "acknowledge", "cheapest_item"),
    ],
)
def test_followup_types(question, expected, intent, known_entities) -> None:
    context = {"last_intent": intent, "entities": {"product": "milk"}, "turn_count": 1}
    assert dialogue._follow_up_type(question, context) == expected


def test_explicit_intent_cues_are_never_followups(known_entities) -> None:
    context = {"last_intent": "biggest_discount", "entities": {}, "turn_count": 1}
    for question in (
        "cheapest milk",
        "bei ya sukari Naivas",
        "price of an iPhone at Naivas",
    ):
        assert dialogue._follow_up_type(question, context) is None


def test_merged_followup_uses_entity_surface_instead_of_group_id(known_entities) -> None:
    question, _merged = dialogue._merged_question(
        "and at Quickmart?",
        {
            "last_intent": "cheapest_item",
            "entities": {"group": "milk-1l", "store": "naivas"},
            "offset": 0,
        },
        "swap_store",
    )

    assert "milk" in question
    assert "milk-1l" not in question
    assert question.endswith("at quickmart")


def test_new_questions_do_not_inherit_the_previous_offer_intent(
    known_entities, monkeypatch
) -> None:
    routed = []
    intent_by_question = {
        "show current offers": "biggest_discount",
        "cheapest milk": "cheapest_item",
        "bei ya sukari naivas": "price_at_store",
        "price of an iphone at naivas": "price_at_store",
    }

    def fake_answer(question: str, offset: int = 0) -> MarketQuestionResponse:
        routed.append(question.casefold())
        intent = intent_by_question[question.casefold()]
        return _response(intent, {"product": "milk"} if "milk" in question else {})

    monkeypatch.setattr(dialogue, "answer_trained_question", fake_answer)
    context = None
    results = []
    for question in intent_by_question:
        result = dialogue.answer_dialogue(question, context)
        results.append(result)
        context = result.context

    assert [result.intent for result in results] == [
        "biggest_discount", "cheapest_item", "price_at_store", "price_at_store"
    ]
    assert routed == list(intent_by_question)


@pytest.mark.parametrize(
    "question",
    ["what is the price of the cheapest soda", "cheapest fizzy drink"],
)
def test_answerable_soft_drink_queries_do_not_ask_for_clarification(
    question, known_entities, monkeypatch
) -> None:
    monkeypatch.setattr(
        trained_assistant,
        "_classify",
        lambda _text: ("cheapest_item", 0.9, None),
    )
    candidates = [item for item in get_listings() if item.category == "soft_drinks"]
    expected = min(
        candidates,
        key=lambda item: item.unit_price if item.unit_price is not None else float("inf"),
    )

    response = dialogue.answer_dialogue(question)

    assert response.needs_clarification is False
    assert expected.product_url in response.answer


def test_unqualified_cheapest_still_requests_a_product(known_entities, monkeypatch) -> None:
    monkeypatch.setattr(
        trained_assistant,
        "_classify",
        lambda _text: ("cheapest_item", 0.9, None),
    )

    response = dialogue.answer_dialogue("cheapest")

    assert response.needs_clarification is True
    assert response.answer.startswith("Which product or group?")


def test_invalid_and_six_turn_context_are_bounded(known_entities, monkeypatch) -> None:
    monkeypatch.setattr(
        dialogue, "answer_trained_question",
        lambda _question, offset=0: _response(entities={"product": "milk"}),
    )
    context = None
    for _ in range(6):
        result = dialogue.answer_dialogue("thanks" if context else "cheapest milk", context)
        context = result.context
    assert context["turn_count"] == 6
    assert (
        dialogue.validate_context({**context, "turn_count": 100})["turn_count"]
        == dialogue.MAX_TURNS
    )
    assert dialogue.validate_context({**context, "offset": -1}) == {}


def test_clarification_can_be_filled_on_next_turn(known_entities, monkeypatch) -> None:
    routed = []
    def fake_answer(question: str, offset: int = 0) -> MarketQuestionResponse:
        routed.append(question)
        return _response(entities={"product": "milk"} if "milk" in question else {})
    monkeypatch.setattr(dialogue, "answer_trained_question", fake_answer)
    first = dialogue.answer_dialogue("cheapest", None)
    assert first.needs_clarification is True
    assert first.context["pending_slot"] == "product"
    second = dialogue.answer_dialogue("milk", first.context)
    assert second.context["pending_slot"] is None
    assert routed[-1] == "cheapest milk"
