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
    prepared = [
        (item, size_signature(item.pack_size),
         set(normalized_name(item.item_name).split()) - stop)
        for item in listings
    ]
    for index, (left, left_size, left_tokens) in enumerate(prepared):
        if left_size is None or not left_tokens:
            continue
        for right, right_size, right_tokens in prepared[index + 1:]:
            if (
                left.supermarket == right.supermarket
                or left_size != right_size
            ):
                continue
            shared = left_tokens & right_tokens
            if not shared:
                continue
            union = left_tokens | right_tokens
            score = len(shared) / len(union)
            # Keep the entire blocked set above a deliberately permissive
            # similarity floor. The label-suggestion step applies its 120-row cap.
            if score >= 0.20:
                pairs.append((score, left, right))
    pairs.sort(key=lambda pair: (-pair[0], pair[1].id, pair[2].id))
    rows = []
    for score, left, right in pairs:
        rows.append({
            "id_a": left.id, "id_b": right.id,
            "store_a": left.supermarket, "store_b": right.supermarket,
            "name_a": left.item_name, "name_b": right.item_name,
            "pack_a": left.pack_size or "", "pack_b": right.pack_size or "",
            "price_a": str(left.price_kes), "price_b": str(right.price_kes),
            "product_url_a": left.product_url, "product_url_b": right.product_url,
            "blocking_similarity": f"{score:.4f}", "label": "",
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
            {"id": row.id, "store": row.supermarket, "item_name": row.item_name,
             "product_url": row.product_url, "label": ""}
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
                     "pack_a", "pack_b", "price_a", "price_b", "product_url_a",
                     "product_url_b", "blocking_similarity", "label"]
    category_headers = ["id", "store", "item_name", "product_url", "label"]
    matches = candidate_pairs()
    categories = category_sample()
    write_csv(LABELS / "match_pairs.csv", matches, match_headers)
    write_csv(LABELS / "category_sample.csv", categories, category_headers)
    print(f"Match candidates: {len(matches)}")
    print(f"Category rows: {len(categories)}")
    print("Human labels remain blank. Enter 1/0 for pairs and an APHRC food_group for categories.")


if __name__ == "__main__":
    main()
