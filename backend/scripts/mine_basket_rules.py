"""Generate labelled synthetic baskets and demonstrate Apriori association rules."""

from __future__ import annotations

import argparse
import csv
import json
import random
from pathlib import Path

from price_check_api.association_rules import association_rules, read_transactions

ROOT = Path(__file__).resolve().parents[1]
STAPLE_GROUPS = ROOT / "data/listings/staple_groups.json"
DEFAULT_OUTPUT = ROOT / "data/baskets/synthetic_baskets.csv"


def generate_synthetic_transactions(
    count: int = 500,
    seed: int = 42,
) -> list[frozenset[str]]:
    """Create reproducible teaching transactions; none are observed purchases."""
    if count < 1:
        raise ValueError("count must be positive")
    definitions = json.loads(STAPLE_GROUPS.read_text(encoding="utf-8"))
    known_items = {row["id"] for row in definitions}
    bread = "bread"
    known_items.add(bread)
    bundles = (
        ({"maize-meal-2kg", "cooking-oil-1l"}, 0.30),
        ({"bread", "milk-1l"}, 0.28),
        ({"milk-1l", "sugar-2kg"}, 0.17),
        ({"maize-meal-2kg", "sugar-2kg"}, 0.15),
        ({"bread", "eggs-tray-15", "milk-1l"}, 0.10),
    )
    if any(not bundle.issubset(known_items) for bundle, _ in bundles):
        raise ValueError("synthetic bundle references an unknown staple-group item")
    rng = random.Random(seed)
    weights = [weight for _, weight in bundles]
    transactions = []
    for _ in range(count):
        selected = set(rng.choices([bundle for bundle, _ in bundles], weights=weights, k=1)[0])
        for item in sorted(known_items - selected):
            if rng.random() < 0.04:
                selected.add(item)
        transactions.append(frozenset(selected))
    return transactions


def write_synthetic_transactions(path: Path, count: int = 500, seed: int = 42) -> None:
    """Persist synthetic example baskets with explicit provenance on every row."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as destination:
        writer = csv.DictWriter(destination, fieldnames=["transaction_id", "item", "source"])
        writer.writeheader()
        for index, transaction in enumerate(generate_synthetic_transactions(count, seed), 1):
            for item in sorted(transaction):
                writer.writerow(
                    {
                        "transaction_id": f"synthetic-{index:04d}",
                        "item": item,
                        "source": "synthetic",
                    }
                )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--transactions", type=int, default=500)
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()
    write_synthetic_transactions(args.output, args.transactions, args.seed)
    transactions = read_transactions(str(args.output))
    rules = association_rules(transactions, min_support=0.02, min_confidence=0.1)
    print(f"Wrote {len(transactions)} labelled synthetic transactions to {args.output}")
    print("Synthetic association rules (not real shopping behavior):")
    for rule in rules[:10]:
        print(
            f"{' + '.join(sorted(rule.antecedent))} -> "
            f"{' + '.join(sorted(rule.consequent))} "
            f"(support={rule.support:.3f}, confidence={rule.confidence:.3f}, lift={rule.lift:.3f})"
        )


if __name__ == "__main__":
    main()
