"""Create explicit blank human-label sheets from the checked-in listing snapshot."""

import csv
import re
from collections import defaultdict
from pathlib import Path

from price_check_api.listings import get_listings, get_uom_map, parse_pack_size

ROOT = Path(__file__).resolve().parents[1]
LABELS = ROOT / "data/labels"


def normalized_name(value: str) -> str:
    return " ".join(re.findall(r"[a-z0-9]+", value.casefold()))


def size_signature(pack: str | None) -> tuple[float, str] | None:
    return parse_pack_size(pack, get_uom_map())


def candidate_pairs() -> list[dict[str, str]]:
    listings = get_listings()
    pairs: list[tuple[float, object, object]] = []
    stop = {"fresh", "natural", "whole", "food", "with", "the", "and", "pack"}
    for index, left in enumerate(listings):
        left_size = size_signature(left.pack_size)
        left_tokens = set(normalized_name(left.item_name).split()) - stop
        if left_size is None or not left_tokens:
            continue
        for right in listings[index + 1:]:
            if (
                left.supermarket == right.supermarket
                or left_size != size_signature(right.pack_size)
            ):
                continue
            right_tokens = set(normalized_name(right.item_name).split()) - stop
            shared = left_tokens & right_tokens
            if not shared:
                continue
            union = left_tokens | right_tokens
            score = len(shared) / len(union)
            pairs.append((score, left, right))
    pairs.sort(key=lambda pair: (-pair[0], pair[1].id, pair[2].id))
    rows = []
    for _, left, right in pairs[:60]:
        rows.append({
            "id_a": left.id, "id_b": right.id,
            "store_a": left.supermarket, "store_b": right.supermarket,
            "name_a": left.item_name, "name_b": right.item_name,
            "pack_a": left.pack_size or "", "pack_b": right.pack_size or "",
            "price_a": str(left.price_kes), "price_b": str(right.price_kes), "label": "",
        })
    return rows


def category_sample() -> list[dict[str, str]]:
    listings = get_listings()
    by_store: dict[str, list] = defaultdict(list)
    for item in listings:
        by_store[item.supermarket].append(item)
    quotas = {"Naivas": 44, "Carrefour": 6, "Quickmart": 10}
    output = []
    for store, rows in by_store.items():
        sample = sorted(rows, key=lambda item: item.id)[:quotas.get(store, 0)]
        output.extend(
            {"id": row.id, "store": row.supermarket, "item_name": row.item_name, "label": ""}
            for row in sample
        )
    return output


def write_csv(path: Path, rows: list[dict[str, str]], headers: list[str]) -> None:
    with path.open("w", encoding="utf-8", newline="") as target:
        writer = csv.DictWriter(target, fieldnames=headers)
        writer.writeheader()
        writer.writerows(rows)


def main() -> None:
    LABELS.mkdir(parents=True, exist_ok=True)
    match_headers = ["id_a", "id_b", "store_a", "store_b", "name_a", "name_b",
                     "pack_a", "pack_b", "price_a", "price_b", "label"]
    category_headers = ["id", "store", "item_name", "label"]
    matches = candidate_pairs()
    categories = category_sample()
    write_csv(LABELS / "match_pairs_to_label.csv", matches, match_headers)
    write_csv(LABELS / "category_sample_to_label.csv", categories, category_headers)
    print(f"Match candidates for human labels: {len(matches)}")
    print(f"Category rows for human labels: {len(categories)}")
    print("Labels remain blank. Enter 1/0 for pairs and an APHRC food_group for categories.")


if __name__ == "__main__":
    main()
