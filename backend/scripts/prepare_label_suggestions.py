"""Add evidence-backed suggestions without filling the human label columns."""

import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from prepare_listings import candidate_pairs, category_sample, write_csv

from price_check_api.listings import get_listings  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
LABELS = ROOT / "data/labels"


def tokens(value: str) -> set[str]:
    return set(re.findall(r"[a-z0-9]+", value.casefold())) - {
        "the", "and", "with", "fresh", "whole", "natural", "pack", "pcs"
    }


def match_rows() -> list[dict[str, str]]:
    listings = get_listings()
    by_id = {item.id: item for item in listings}
    rows = candidate_pairs()[:50]
    used = {(row["id_a"], row["id_b"]) for row in rows}
    negatives = []
    for index, left in enumerate(listings):
        left_tokens = tokens(left.item_name)
        if not left_tokens or not left.pack_size:
            continue
        for right in listings[index + 1:]:
            key = (left.id, right.id)
            if left.supermarket == right.supermarket or key in used:
                continue
            right_tokens = tokens(right.item_name)
            shared = left_tokens & right_tokens
            if len(shared) < 2 or left.pack_size == right.pack_size:
                continue
            negatives.append((len(shared), left, right, sorted(shared)))
    negatives.sort(key=lambda row: (-row[0], row[1].id, row[2].id))
    for _, left, right, shared in negatives[:10]:
        rows.append({
            "id_a": left.id, "id_b": right.id,
            "store_a": left.supermarket, "store_b": right.supermarket,
            "name_a": left.item_name, "name_b": right.item_name,
            "pack_a": left.pack_size or "", "pack_b": right.pack_size or "",
            "price_a": str(left.price_kes), "price_b": str(right.price_kes),
            "label": "",
            "suggested_label": "0",
            "suggestion_confidence": "high",
            "evidence": f"Shared name tokens {', '.join(shared[:3])}; pack sizes differ.",
        })
    for row in rows:
        if row.get("suggested_label"):
            continue
        left, right = by_id[row["id_a"]], by_id[row["id_b"]]
        same_name = tokens(left.item_name) == tokens(right.item_name)
        same_pack = left.pack_size == right.pack_size
        label = "1" if same_name and same_pack else "0"
        confidence = "high" if same_name and same_pack else "medium"
        evidence = (
            "Normalized item names and pack sizes match."
            if label == "1"
            else "Names or pack sizes differ; verify brand and variant."
        )
        row.update(suggested_label=label, suggestion_confidence=confidence, evidence=evidence)
    return rows[:60]


def category_rows() -> list[dict[str, str]]:
    rows = category_sample()
    rules = [
        (r"milk|yoghurt|yogurt|cheese|butter|margarine|egg", "Milk and Dairy Products"),
        (r"juice|soda|cola|water|tea|coffee|drink", "Beverages - Sweetened"),
        (r"rice|maize|flour|pasta|noodle|bread|cereal", "Cereals and Grain products"),
        (r"bean|lentil|pea|ndengu", "Legumes and Pulses"),
        (r"oil|margarine|ghee", "Oils and Fat"),
        (r"sugar|honey|jam", "Sugar and Sweetened Products"),
        (
            r"tomato|onion|potato|avocado|banana|mango|fruit|vegetable|spinach",
            "Fruits and Vegetables",
        ),
        (r"chocolate|sweet|candy|biscuit|cookie|cake", "Sweet Snacks/Sweet Baked Foods"),
        (r"chicken|beef|fish|sausage", "Meat, Poultry and Eggs"),
    ]
    for row in rows:
        match = next(((pattern, label) for pattern, label in rules
                      if re.search(pattern, row["item_name"], re.I)), None)
        if match:
            pattern, label = match
            row.update(suggested_label=label, suggestion_confidence="medium",
                       evidence=f"Name keyword(s) matched category rule /{pattern}/.")
        else:
            row.update(suggested_label="", suggestion_confidence="low",
                       evidence="No specific category keyword matched; needs human review.")
    return rows


def main() -> None:
    LABELS.mkdir(parents=True, exist_ok=True)
    pairs = match_rows()
    categories = category_rows()
    pair_fields = ["id_a", "id_b", "store_a", "store_b", "name_a", "name_b",
                   "pack_a", "pack_b", "price_a", "price_b", "label",
                   "suggested_label", "suggestion_confidence", "evidence"]
    category_fields = ["id", "store", "item_name", "label", "suggested_label",
                       "suggestion_confidence", "evidence"]
    write_csv(LABELS / "match_pairs.csv", pairs, pair_fields)
    write_csv(LABELS / "category_sample.csv", categories, category_fields)
    print(f"Pair suggestions: {len(pairs)}; human labels still blank")
    print(f"Category suggestions: {len(categories)}; human labels still blank")
    hard_negatives = sum("sizes differ" in row["evidence"] for row in pairs)
    print(f"Hard-negative size-mismatch suggestions: {hard_negatives}")


if __name__ == "__main__":
    main()
