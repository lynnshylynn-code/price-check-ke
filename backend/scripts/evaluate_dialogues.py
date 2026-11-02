"""Replay scripted multi-turn dialogues against the trained assistant."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

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
    if kind == "unknown_store_declared":
        store = str(check["store"])
        answer = response.answer.casefold()
        return store.casefold() in answer and "not in the snapshot" in answer.casefold()
    raise ValueError(f"Unsupported dialogue check: {kind}")


def evaluate(
    path: Path,
    listings_by_url: dict[str, Any],
    title: str,
) -> dict[str, float | int]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    turn_total = turn_passed = dialogue_total = dialogue_passed = 0
    for dialogue in payload["dialogues"]:
        context = None
        success = True
        for turn in dialogue["turns"]:
            response = answer_dialogue(turn["user"], context)
            context = response.context
            turn_checks = turn.get("CHECKS", [])
            passed = all(
                _check(check, response, listings_by_url) for check in turn_checks
            )
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
    listings_by_url = {item.product_url: item for item in get_listings()}
    metrics = {
        "ai_written": evaluate(ROOT / "data/assistant/dialogues_eval.json", listings_by_url,
                                "AI-written dialogue evaluation")
    }
    human = ROOT / "data/assistant/human_dialogues.json"
    if human.is_file():
        metrics["human_written"] = evaluate(
            human, listings_by_url, "Human-written dialogue evaluation"
        )
    (ROOT / "models/dialogue_metrics.json").write_text(
        json.dumps(metrics, indent=2), encoding="utf-8"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
