import csv
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from price_check_api import dialogue, trained_assistant
from price_check_api.listings import get_listings
from price_check_api.main import app

client = TestClient(app)
BACKEND = Path(__file__).parents[1]


def test_unknown_item_is_not_a_clarification() -> None:
    response = dialogue.answer_dialogue("price of an iPhone at Naivas")

    assert response.needs_clarification is False
    assert "is not in the snapshot" in response.answer
    assert "iphone" in response.answer.casefold()


def test_bare_store_question_still_asks_for_product() -> None:
    response = dialogue.answer_dialogue("What is the price at Quickmart?")

    assert response.needs_clarification is True
    assert "Which product or group at Quickmart" in response.answer


def test_no_result_message_names_the_store(monkeypatch: pytest.MonkeyPatch) -> None:
    assert not any(
        item.supermarket == "Naivas" and "isinya" in item.item_name.casefold()
        for item in get_listings()
    )
    monkeypatch.setattr(
        trained_assistant,
        "_classify",
        lambda _question: ("price_at_store", 0.9, None),
    )

    response = dialogue.answer_dialogue("how much is Isinya eggs at Naivas")

    assert "at Naivas" in response.answer
    assert "No matching advertised listing" in response.answer


def test_unknown_store_is_named() -> None:
    response = dialogue.answer_dialogue("price of sugar at Tuskys")

    assert "Tuskys" in response.answer
    assert "is not in the snapshot" in response.answer


def test_unknown_store_follow_up_is_named() -> None:
    first = dialogue.answer_dialogue("cheapest sugar")
    response = dialogue.answer_dialogue("at Tuskys?", first.context)

    assert "Tuskys" in response.answer
    assert "is not in the snapshot" in response.answer


def test_explain_restates_cited_prices() -> None:
    first = dialogue.answer_dialogue("what is the price of the cheapest soda")
    response = dialogue.answer_dialogue(
        "Why this result?", first.context, follow_up_action="explain"
    )
    listings_by_url = {item.product_url: item for item in get_listings()}
    cited = [
        listings_by_url[str(source.url)]
        for source in first.sources
        if source.name == "Kenya supermarket listing snapshot"
        and str(source.url) in listings_by_url
    ]

    assert cited
    for listing in cited[:5]:
        assert f"KES {listing.price_kes:g}" in response.answer
        assert listing.supermarket in response.answer


def test_follow_up_action_without_context() -> None:
    response = dialogue.answer_dialogue(
        "Why this result?", None, follow_up_action="explain"
    )

    assert response.answer == "Ask a question first, then I can explain it or show more."
    assert response.needs_clarification is False


def test_follow_up_action_skips_text_classifier(monkeypatch: pytest.MonkeyPatch) -> None:
    first = dialogue.answer_dialogue("cheapest soda")
    monkeypatch.setattr(
        dialogue,
        "_follow_up_type",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(AssertionError()),
    )

    dialogue.answer_dialogue(
        "anything else?", first.context, follow_up_action="show_more"
    )


def test_refine_store_action() -> None:
    first = dialogue.answer_dialogue("cheapest soda")
    response = dialogue.answer_dialogue(
        "Only at Carrefour?",
        first.context,
        follow_up_action="refine_store",
        store="Carrefour",
    )
    listing_stores = {item.product_url: item.supermarket for item in get_listings()}
    cited_urls = [
        url for url in listing_stores if url in response.answer
    ]

    assert (cited_urls and all(listing_stores[url] == "Carrefour" for url in cited_urls)) or (
        "No previous result matched Carrefour" in response.answer
    )


def test_suggestion_actions_match_suggestions() -> None:
    responses = [
        dialogue.answer_dialogue("cheapest soda"),
        dialogue.answer_dialogue("food inflation today"),
        dialogue.answer_dialogue("maize price in Nairobi"),
    ]

    for response in responses:
        assert len(response.suggestion_actions) == len(response.suggestions)
        assert [action.label for action in response.suggestion_actions] == response.suggestions


def test_api_accepts_and_validates_follow_up_action() -> None:
    valid = client.post(
        "/api/v1/assistant/ask",
        json={"question": "Why this result?", "follow_up_action": "explain"},
    )
    invalid = client.post(
        "/api/v1/assistant/ask",
        json={"question": "Why this result?", "follow_up_action": "delete_everything"},
    )

    assert valid.status_code == 200
    assert invalid.status_code == 422


def test_followup_templates_have_enough_families() -> None:
    with (BACKEND / "data/assistant/followup_templates.csv").open(
        encoding="utf-8", newline=""
    ) as stream:
        rows = list(csv.DictReader(stream))
    families_by_label: dict[str, set[str]] = {}
    for row in rows:
        families_by_label.setdefault(row["label"], set()).add(row["family_id"])

    assert len(families_by_label["show_more"]) >= 12
    assert len(families_by_label["new_question"]) >= 12
