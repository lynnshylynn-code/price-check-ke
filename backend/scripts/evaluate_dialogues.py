"""Replay scripted multi-turn dialogues against the trained assistant."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from price_check_api import trained_assistant  # noqa: E402
from price_check_api.assistant_model import load_assistant_model  # noqa: E402
from price_check_api.dialogue import answer_dialogue  # noqa: E402
from price_check_api.listings import get_listings  # noqa: E402


def _check(
    check: dict[str, Any],
    response: Any,
    listings_by_url: dict[str, Any],
) -> bool:
    kind = check["type"]
    if kind == "response_shape":
        return bool(response.answer.strip()) and isinstance(response.context, dict)
    if kind == "intent_is":
        return response.intent == check["intent"]
    if kind == "follow_up_type_is":
        return response.follow_up_type == check["follow_up_type"]
    if kind == "no_advice_or_forecast":
        answer = response.answer.casefold()
        return not any(term in answer for term in ("i predict", "you should buy", "will cost"))
    if kind == "listing_sources_in_snapshot":
        listing_sources = [str(source.url) for source in response.sources
                           if source.name == "Kenya supermarket listing snapshot"]
        return all(url in listings_by_url for url in listing_sources)
    if kind == "cited_listing_prices_match_snapshot":
        listing_sources = [str(source.url) for source in response.sources
                           if source.name == "Kenya supermarket listing snapshot"]
        if not listing_sources:
            return True
        answer = response.answer
        return all(
            f"{listings_by_url[url].price_kes:g}" in answer
            for url in listing_sources
        )
    if kind == "named_store_mentioned":
        store = str(check["store"])
        return store.casefold() in response.answer.casefold()
    if kind == "no_listing_price":
        return "kes" not in response.answer.casefold()
    if kind == "source_stores_present":
        urls = [
            str(source.url)
            for source in response.sources
            if source.name == "Kenya supermarket listing snapshot"
        ]
        stores = {listings_by_url[url].supermarket.casefold() for url in urls}
        return all(str(store).casefold() in stores for store in check["stores"])
    if kind == "matching_listing_at_store":
        store = str(check["store"]).casefold()
        tokens = [str(token).casefold() for token in check.get("name_tokens", [])]
        candidates = [
            item
            for item in listings_by_url.values()
            if item.supermarket.casefold() == store
            and all(token in item.item_name.casefold() for token in tokens)
        ]
        if not candidates:
            return False
        expected = min(
            candidates,
            key=lambda item: (
                item.unit_price if item.unit_price is not None else float("inf"),
                item.price_kes,
            ),
        )
        urls = {
            str(source.url)
            for source in response.sources
            if source.name == "Kenya supermarket listing snapshot"
        }
        return expected.product_url in urls and f"KES {expected.price_kes:g}" in response.answer
    if kind == "no_matching_listing_at_store":
        store = str(check["store"]).casefold()
        tokens = [str(token).casefold() for token in check.get("name_tokens", [])]
        candidates = [
            item
            for item in listings_by_url.values()
            if item.supermarket.casefold() == store
            and all(token in item.item_name.casefold() for token in tokens)
        ]
        answer = response.answer.casefold()
        return not candidates and "no matching" in answer
    if kind == "any_matching_listing_at_store":
        store = str(check["store"]).casefold()
        tokens = [str(token).casefold() for token in check.get("name_tokens", [])]
        candidates = [
            item
            for item in listings_by_url.values()
            if item.supermarket.casefold() == store
            and all(token in item.item_name.casefold() for token in tokens)
        ]
        urls = {
            str(source.url)
            for source in response.sources
            if source.name == "Kenya supermarket listing snapshot"
        }
        return any(item.product_url in urls for item in candidates)
    if kind == "category_listing_present":
        category = str(check["category"])
        store = str(check.get("store", "")).casefold()
        candidates = [
            item
            for item in listings_by_url.values()
            if item.category == category
            and (not store or item.supermarket.casefold() == store)
        ]
        if not candidates:
            return False
        units = {item.unit for item in candidates}
        comparable = len(units) == 1 and None not in units and all(
            item.unit_price is not None for item in candidates
        )
        expected = min(
            candidates,
            key=lambda item: (
                item.unit_price if comparable and item.unit_price is not None
                else item.price_kes,
                item.price_kes,
            ),
        )
        urls = {
            str(source.url)
            for source in response.sources
            if source.name == "Kenya supermarket listing snapshot"
        }
        return expected.product_url in urls
    if kind == "unknown_store_declared":
        store = str(check["store"])
        answer = response.answer.casefold()
        return store.casefold() in answer and "not in the snapshot" in answer.casefold()
    raise ValueError(f"Unsupported dialogue check: {kind}")


def evaluate(
    path: Path,
    listings_by_url: dict[str, Any],
    title: str,
    dialogue_ids: set[str] | None = None,
) -> dict[str, float | int]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    dialogues = payload["dialogues"]
    if dialogue_ids is not None:
        dialogues = [item for item in dialogues if item["dialogue_id"] in dialogue_ids]
    turn_total = turn_passed = dialogue_total = dialogue_passed = 0
    for dialogue in dialogues:
        context = None
        success = True
        for turn in dialogue["turns"]:
            response = answer_dialogue(turn["user"], context)
            context = response.context
            turn_checks = turn.get("CHECKS", [])
            failed_checks = [
                check for check in turn_checks if not _check(check, response, listings_by_url)
            ]
            passed = not failed_checks
            if failed_checks:
                print(f"FAILED checks for {dialogue['dialogue_id']}: {failed_checks}")
            turn_total += 1
            turn_passed += int(passed)
            success = success and passed
            print(f"{dialogue['dialogue_id']}: {turn['user']} -> {response.answer}")
        dialogue_total += 1
        dialogue_passed += int(success)
    turn_accuracy = turn_passed / turn_total if turn_total else 0.0
    success_rate = dialogue_passed / dialogue_total if dialogue_total else 0.0
    print(f"{title}: turn accuracy={turn_accuracy:.4f} ({turn_passed}/{turn_total}); "
          f"dialogue success={success_rate:.4f} ({dialogue_passed}/{dialogue_total})")
    return {
        "turns_passed": turn_passed,
        "turns": turn_total,
        "turn_accuracy": turn_accuracy,
        "dialogues_passed": dialogue_passed,
        "dialogues": dialogue_total,
        "dialogue_success_rate": success_rate,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--dialogue-id",
        action="append",
        dest="dialogue_ids",
        help="Evaluate only this dialogue ID (may be repeated).",
    )
    arguments = parser.parse_args()
    assistant_state = load_assistant_model()
    # Reuse the same loaded artifact across scripted turns instead of joblib-loading per question.
    trained_assistant.load_assistant_model = lambda: assistant_state
    listings_by_url = {item.product_url: item for item in get_listings()}
    dialogue_filter = set(arguments.dialogue_ids) if arguments.dialogue_ids else None
    metrics = {
        "ai_written": evaluate(
            ROOT / "data/assistant/dialogues_eval.json",
            listings_by_url,
            "AI-written dialogue evaluation",
            dialogue_filter,
        )
    }
    human = ROOT / "data/assistant/human_dialogues.json"
    if human.is_file() and dialogue_filter is None:
        metrics["human_written"] = evaluate(
            human, listings_by_url, "Human-written dialogue evaluation"
        )
    if dialogue_filter is None:
        (ROOT / "models/dialogue_metrics.json").write_text(
            json.dumps(metrics, indent=2), encoding="utf-8"
        )
    return 0


if __name__ == "__main__":
    sys.exit(main())
