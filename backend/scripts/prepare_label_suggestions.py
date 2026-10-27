"""Build reviewer-ready suggestions without filling human label columns."""

import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from prepare_listings import candidate_pairs, category_sample, size_signature, write_csv  # noqa: E402

from price_check_api.listings import get_listings  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
LABELS = ROOT / "data/labels"
PAIR_LIMIT = 120
HARD_NEGATIVE_COUNT = 20

FALLBACK_FOOD_GROUPS = [
    "Baby Foods",
    "Beverages - Sweetened",
    "Beverages - Unsweetened",
    "Cereals and Grain products",
    "Condiments, Spices and Herbs",
    "Confectionery (Candy, Gums, Chocolates)",
    "Fish and Sea Food",
    "Food Colour/Flavour and Baking Additives",
    "Fruits and Vegetables",
    "Legumes and Pulses",
    "Meat, Poultry and Eggs",
    "Milk and Dairy Products",
    "Mixed Dishes and Fast Foods",
    "Nuts and Seeds",
    "Oils and Fat",
    "Savoury snacks",
    "Starchy Roots and Tubers",
    "Sugar and Sweetened Products",
    "Sweet Snacks/Sweet Baked Foods",
]

CATEGORY_RULES = [
    (r"baby food|infant formula|baby cereal", "Baby Foods"),
    (r"juice|soda|cola|soft drink|energy drink|sweetened", "Beverages - Sweetened"),
    (r"water|tea|coffee|unsweetened", "Beverages - Unsweetened"),
    (r"rice|maize|flour|pasta|noodle|bread|cereal|wheat|oat", "Cereals and Grain products"),
    (r"spice|seasoning|salt|sauce|vinegar|stock cube|tomato paste", "Condiments, Spices and Herbs"),
    (r"chocolate|candy|gum|confection|sweet", "Confectionery (Candy, Gums, Chocolates)"),
    (r"fish|tuna|sardine|seafood", "Fish and Sea Food"),
    (
        r"baking powder|food colour|flavour|yeast|essence",
        "Food Colour/Flavour and Baking Additives",
    ),
    (
        r"tomato|onion|potato|avocado|banana|mango|fruit|vegetable|spinach|sukuma",
        "Fruits and Vegetables",
    ),
    (r"bean|lentil|pea|ndengu|pulse", "Legumes and Pulses"),
    (r"chicken|beef|meat|sausage|egg", "Meat, Poultry and Eggs"),
    (r"milk|yoghurt|yogurt|cheese|butter|margarine", "Milk and Dairy Products"),
    (r"pizza|burger|ready meal|meal|fast food", "Mixed Dishes and Fast Foods"),
    (r"nut|peanut|groundnut|seed", "Nuts and Seeds"),
    (r"oil|ghee|fat", "Oils and Fat"),
    (r"crisps|chips|savoury|savory|cracker", "Savoury snacks"),
    (r"cassava|yam|sweet potato|arrowroot|taro", "Starchy Roots and Tubers"),
    (r"sugar|honey|syrup|jam", "Sugar and Sweetened Products"),
    (r"biscuit|cookie|cake|pastry|sweet baked", "Sweet Snacks/Sweet Baked Foods"),
]
NON_FOOD = re.compile(
    r"\b(detergent|soap|tissue|toothpaste|shampoo|lotion|bleach|cleaner|appliance)\b", re.I
)


def tokens(value: str) -> set[str]:
    return set(re.findall(r"[a-z0-9]+", value.casefold())) - {
        "the",
        "and",
        "with",
        "fresh",
        "whole",
        "natural",
        "pack",
        "pcs",
    }


def match_rows() -> list[dict[str, str]]:
    listings = get_listings()
    by_id = {item.id: item for item in listings}
    candidates = candidate_pairs()
    rows: list[dict[str, str]] = []
    used: set[tuple[str, str]] = set()

    def make_row(
        left,
        right,
        hard_negative: bool = False,
        blocking_score: float | None = None,
    ) -> dict[str, str]:
        left_tokens, right_tokens = tokens(left.item_name), tokens(right.item_name)
        score = (
            blocking_score
            if blocking_score is not None
            else (len(left_tokens & right_tokens) / max(1, len(left_tokens | right_tokens)))
        )
        same_name = tokens(left.item_name) == tokens(right.item_name)
        same_size = size_signature(left.pack_size) is not None and size_signature(
            left.pack_size
        ) == size_signature(right.pack_size)
        suggested = "1" if same_name and same_size and not hard_negative else "0"
        if hard_negative:
            evidence = "Same leading brand token; distinct variant and pack size."
            confidence = "high"
        elif suggested == "1":
            evidence = "Normalized item tokens and pack size match across stores."
            confidence = "high"
        else:
            evidence = "Blocked by shared name tokens and compatible pack; check variant."
            confidence = "low"
        return {
            "id_a": left.id,
            "id_b": right.id,
            "store_a": left.supermarket,
            "store_b": right.supermarket,
            "name_a": left.item_name,
            "name_b": right.item_name,
            "pack_a": left.pack_size or "",
            "pack_b": right.pack_size or "",
            "price_a": str(left.price_kes),
            "price_b": str(right.price_kes),
            "blocking_similarity": f"{score:.4f}",
            "product_url_a": left.product_url,
            "product_url_b": right.product_url,
            "label": "",
            "suggested_label": suggested,
            "suggestion_confidence": confidence,
            "evidence": evidence,
        }

    # Preserve every row found by the shared-token/equal-normalized-pack blocking
    # step up to the 100-row candidate allowance; reserve 20 slots for hard negatives.
    for candidate in candidates[: PAIR_LIMIT - HARD_NEGATIVE_COUNT]:
        left, right = by_id[candidate["id_a"]], by_id[candidate["id_b"]]
        rows.append(make_row(left, right, blocking_score=float(candidate["blocking_similarity"])))
        used.add((left.id, right.id))

    hard_negatives = []
    prepared = [(item, tokens(item.item_name), size_signature(item.pack_size)) for item in listings]
    for index, (left, left_tokens, left_size) in enumerate(prepared):
        if not left_tokens:
            continue
        for right, right_tokens, right_size in prepared[index + 1 :]:
            if left.supermarket != right.supermarket:
                continue
            if left_size == right_size or (left.id, right.id) in used:
                continue
            shared = left_tokens & right_tokens
            if not shared:
                continue
            # Same leading token is a conservative brand proxy, then prefer the
            # most textually similar different size/variant rows.
            if left.item_name.split()[0].casefold() != right.item_name.split()[0].casefold():
                continue
            similarity = len(shared) / max(1, len(left_tokens | right_tokens))
            hard_negatives.append((similarity, left, right))
    hard_negatives.sort(key=lambda pair: (-pair[0], pair[1].id, pair[2].id))
    for similarity, left, right in hard_negatives[:HARD_NEGATIVE_COUNT]:
        rows.append(make_row(left, right, hard_negative=True, blocking_score=similarity))
    return rows[:PAIR_LIMIT]


def food_group_vocabulary() -> list[str]:
    workbook = ROOT / "data/listings/private/APHRC_supermarket_item_catalogue_and_dictionary.xlsx"
    try:
        import pandas as pd

        values = pd.read_excel(workbook, sheet_name="unique_items").food_group.dropna()
        vocabulary = sorted({str(value).strip() for value in values if str(value).strip()})
        if vocabulary:
            return vocabulary
    except (ImportError, OSError, ValueError, AttributeError):
        pass
    return FALLBACK_FOOD_GROUPS


def category_rows() -> list[dict[str, str]]:
    listings = {item.id: item for item in get_listings()}
    vocabulary = set(food_group_vocabulary())
    output = []
    for row in category_sample():
        item = listings[row["id"]]
        match = next(
            (
                (pattern, group)
                for pattern, group in CATEGORY_RULES
                if group in vocabulary and re.search(pattern, item.item_name, re.I)
            ),
            None,
        )
        if NON_FOOD.search(item.item_name) and "Non-food" in vocabulary:
            label, confidence, evidence = "Non-food", "high", "Name identifies a non-food product."
        elif match:
            pattern, label = match
            confidence = "high" if len(tokens(item.item_name)) >= 3 else "medium"
            evidence = f"Name keyword matched {label} rule."
        else:
            label = (
                "Mixed Dishes and Fast Foods"
                if "Mixed Dishes and Fast Foods" in vocabulary
                else sorted(vocabulary)[0]
            )
            confidence = "low"
            evidence = "No specific food-group keyword; broad fallback needs review."
        output.append(
            {
                **row,
                "product_url": item.product_url,
                "suggested_label": label,
                "suggestion_confidence": confidence,
                "evidence": evidence,
            }
        )
    return output


def main() -> None:
    LABELS.mkdir(parents=True, exist_ok=True)
    pairs = match_rows()
    categories = category_rows()
    pair_fields = [
        "id_a",
        "id_b",
        "store_a",
        "store_b",
        "name_a",
        "name_b",
        "pack_a",
        "pack_b",
        "price_a",
        "price_b",
        "blocking_similarity",
        "product_url_a",
        "product_url_b",
        "label",
        "suggested_label",
        "suggestion_confidence",
        "evidence",
    ]
    category_fields = [
        "id",
        "store",
        "item_name",
        "product_url",
        "label",
        "suggested_label",
        "suggestion_confidence",
        "evidence",
    ]
    write_csv(LABELS / "match_pairs.csv", pairs, pair_fields)
    write_csv(LABELS / "category_sample.csv", categories, category_fields)
    print(f"Pair candidates: {len(pairs)}")
    print(f"Pair suggestions = 1: {sum(row['suggested_label'] == '1' for row in pairs)}")
    print(
        "Hard-negative candidates: "
        f"{sum('Same leading brand token' in row['evidence'] for row in pairs)}"
    )
    print(
        f"Category suggestions: {len(categories)}; all nonblank: "
        f"{all(row['suggested_label'] for row in categories)}"
    )
    print(f"Human labels remain blank: {all(not row['label'] for row in pairs + categories)}")


if __name__ == "__main__":
    main()
