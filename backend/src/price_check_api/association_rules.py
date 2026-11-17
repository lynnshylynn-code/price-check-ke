"""Apriori association rules for clearly labelled synthetic basket examples."""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from itertools import combinations
from math import ceil

Itemset = frozenset[str]
Transaction = frozenset[str]


@dataclass(frozen=True)
class AssociationRule:
    antecedent: Itemset
    consequent: Itemset
    support: float
    confidence: float
    lift: float


def mine_frequent_itemsets(
    transactions: Iterable[Iterable[str]],
    min_support: float = 0.01,
) -> dict[Itemset, float]:
    """Mine frequent sets using Apriori's downward-closure property."""
    if not 0 < min_support <= 1:
        raise ValueError("min_support must be in (0, 1]")
    rows = tuple(frozenset(item.strip() for item in row if item.strip()) for row in transactions)
    if not rows:
        return {}
    minimum_count = ceil(min_support * len(rows))
    item_counts: dict[Itemset, int] = {}
    for row in rows:
        for item in row:
            key = frozenset((item,))
            item_counts[key] = item_counts.get(key, 0) + 1
    frequent = {
        itemset: count / len(rows)
        for itemset, count in item_counts.items()
        if count >= minimum_count
    }
    previous = set(frequent)
    size = 2
    while previous:
        candidates = {
            left | right
            for left, right in combinations(sorted(previous, key=lambda value: sorted(value)), 2)
            if len(left | right) == size
            and all(frozenset(part) in previous for part in combinations(left | right, size - 1))
        }
        counts = {
            candidate: sum(candidate.issubset(row) for row in rows)
            for candidate in candidates
        }
        next_level = {
            itemset: count / len(rows)
            for itemset, count in counts.items()
            if count >= minimum_count
        }
        frequent.update(next_level)
        previous = set(next_level)
        size += 1
    return frequent


def association_rules(
    transactions: Iterable[Iterable[str]],
    *,
    min_support: float = 0.01,
    min_confidence: float = 0.1,
) -> tuple[AssociationRule, ...]:
    """Return Apriori rules with transaction support, confidence, and lift."""
    if not 0 <= min_confidence <= 1:
        raise ValueError("min_confidence must be in [0, 1]")
    rows = tuple(frozenset(item.strip() for item in row if item.strip()) for row in transactions)
    if not rows:
        return ()
    support = mine_frequent_itemsets(rows, min_support)
    rules: list[AssociationRule] = []
    for itemset, joint_support in support.items():
        if len(itemset) < 2:
            continue
        ordered = sorted(itemset)
        for size in range(1, len(ordered)):
            for antecedent_values in combinations(ordered, size):
                antecedent = frozenset(antecedent_values)
                consequent = itemset - antecedent
                antecedent_support = support.get(antecedent, 0.0)
                consequent_support = support.get(consequent, 0.0)
                if not antecedent_support or not consequent_support:
                    continue
                confidence = joint_support / antecedent_support
                if confidence >= min_confidence:
                    rules.append(
                        AssociationRule(
                            antecedent,
                            consequent,
                            joint_support,
                            confidence,
                            confidence / consequent_support,
                        )
                    )
    return tuple(
        sorted(
            rules,
            key=lambda rule: (
                -rule.confidence,
                -rule.lift,
                tuple(sorted(rule.antecedent)),
                tuple(sorted(rule.consequent)),
            ),
        )
    )


def read_transactions(path: str) -> tuple[Transaction, ...]:
    """Read synthetic transaction rows with transaction_id and item columns."""
    import csv
    from pathlib import Path

    transactions: dict[str, set[str]] = {}
    with Path(path).open(encoding="utf-8-sig", newline="") as source:
        reader = csv.DictReader(source)
        if not {"transaction_id", "item", "source"}.issubset(reader.fieldnames or []):
            raise ValueError("transaction file must include transaction_id, item, and source")
        for row in reader:
            if row["source"] != "synthetic":
                raise ValueError("association mining accepts only labelled synthetic rows")
            transactions.setdefault(row["transaction_id"], set()).add(row["item"])
    return tuple(frozenset(items) for _, items in sorted(transactions.items()))
