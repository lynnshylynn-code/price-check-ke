"""Measure slot-to-catalogue linking separately on synthetic and held-out rows."""

from __future__ import annotations

import csv
import json
from pathlib import Path

from price_check_api.trained_assistant import (
    _extract,
    _resolve_product,
    _resolve_store,
    _slot_values,
)

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data/assistant"


def _expected(row: dict[str, str], heldout: bool) -> dict[str, str]:
    if not heldout:
        return json.loads(row["entities"])
    result = {}
    for pair in row.get("expected_entities", "").split(";"):
        if "=" in pair:
            key, value = pair.split("=", 1)
            result[key.strip()] = value.strip()
    return result


def _linked(question: str, key: str) -> str | None:
    if key == "product":
        unknown = _extract(question, "unknown_product")
        if unknown:
            return "not in the snapshot"
        canonical, _label, _score = _resolve_product(question)
        return canonical
    if key in {"store", "store2"}:
        store, _confidence, unknown = _resolve_store(question)
        return "not in the snapshot" if unknown else store
    if key in {"commodity", "county", "county2", "group", "group2", "category", "month"}:
        row = _extract(question, key) or (
            _extract(question, "commodity_sw") if key == "commodity" else None
        )
        return row["canonical"] if row else None
    return None


def evaluate(rows: list[dict[str, str]], heldout: bool) -> dict[str, int | float]:
    correct = total = unknown_total = unknown_correct = 0
    for row in rows:
        expected = _expected(row, heldout)
        for key, value in expected.items():
            if key in {"unknown_product", "other_store"}:
                link_key = "product" if key == "unknown_product" else "store"
                actual = _linked(row["question"], link_key)
                total += 1
                unknown_total += 1
                correct += int(actual == "not in the snapshot")
                unknown_correct += int(actual == "not in the snapshot")
                continue
            if not value:
                continue
            if value.upper().startswith("UNKNOWN:"):
                value = value.split(":", 1)[1]
            slot = (
                "unknown_product"
                if key == "product"
                else "other_store"
                if key in {"store", "store2"}
                else ""
            )
            unknown_values = {
                item["surface_form"].casefold() for item in _slot_values().get(slot, [])
            }
            target = (
                "not in the snapshot"
                if value.casefold() in {"unknown", "not in snapshot"} | unknown_values
                else value
            )
            actual = _linked(row["question"], key)
            total += 1
            correct += int(actual is not None and actual.casefold() == target.casefold())
            if target == "not in the snapshot":
                unknown_total += 1
                unknown_correct += int(actual == target)
    return {
        "entities": total,
        "correct": correct,
        "accuracy": correct / total if total else 0.0,
        "deliberately_unknown": unknown_total,
        "unknown_resolved_correctly": unknown_correct,
    }


def main() -> None:
    results = {}
    for split in ("validation", "test"):
        with (DATA / "splits" / f"{split}_questions.csv").open(
            encoding="utf-8", newline=""
        ) as source:
            results[f"synthetic_{split}"] = evaluate(list(csv.DictReader(source)), False)
    with (DATA / "heldout_test_questions.csv").open(encoding="utf-8", newline="") as source:
        results["AI-written held-out set"] = evaluate(list(csv.DictReader(source)), True)
    print(json.dumps(results, indent=2))


if __name__ == "__main__":
    main()
