"""Comparable listing groups used by the optimizer and AI tools."""

from __future__ import annotations

import csv
import hashlib
import json
import math
import re
from collections import Counter
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

from .listings import Listing, get_listings, get_uom_map, parse_pack_size


@dataclass(frozen=True)
class ComparableGroup:
    id: str
    label: str
    basis: str
    listings: tuple[Listing, ...]


def normalize_name(value: str) -> str:
    return " ".join(re.findall(r"[a-z0-9]+", value.casefold()))


def _size_signature(value: str | None) -> tuple[float, str] | None:
    return parse_pack_size(value, get_uom_map())


def _match_score(left: str, right: str) -> float:
    def normalize_sizes(value: str) -> str:
        return re.sub(r"(\d)\s+(kg|g|ml|l)\b", r"\1\2", value.casefold())

    def terms(value: str) -> list[str]:
        words = re.findall(r"(?u)\b\w\w+\b", normalize_sizes(value))
        return words + [f"{a} {b}" for a, b in zip(words, words[1:], strict=False)]

    left_terms, right_terms = terms(left), terms(right)
    left_counts, right_counts = Counter(left_terms), Counter(right_terms)
    vocabulary = set(left_counts) | set(right_counts)
    left_vector, right_vector = [], []
    for term in vocabulary:
        document_frequency = int(term in left_counts) + int(term in right_counts)
        inverse_frequency = math.log(3 / (document_frequency + 1)) + 1
        left_vector.append(left_counts[term] * inverse_frequency)
        right_vector.append(right_counts[term] * inverse_frequency)
    left_norm = math.sqrt(sum(value * value for value in left_vector))
    right_norm = math.sqrt(sum(value * value for value in right_vector))
    cosine = (
        sum(a * b for a, b in zip(left_vector, right_vector, strict=True))
        / (left_norm * right_norm)
        if left_norm and right_norm
        else 0.0
    )
    left_words = set(re.findall(r"[a-z0-9]+", normalize_sizes(left)))
    right_words = set(re.findall(r"[a-z0-9]+", normalize_sizes(right)))
    if not left_words or not right_words:
        return 0.0
    dice = 2 * len(left_words & right_words) / (len(left_words) + len(right_words))
    return (cosine + dice) / 2


def _groups_from_matches(items: tuple[Listing, ...]) -> list[ComparableGroup]:
    parent = {item.id: item.id for item in items}

    def find(identifier: str) -> str:
        while parent[identifier] != identifier:
            parent[identifier] = parent[parent[identifier]]
            identifier = parent[identifier]
        return identifier

    def union(left: str, right: str) -> None:
        a, b = find(left), find(right)
        if a != b:
            parent[max(a, b)] = min(a, b)

    by_exact: dict[tuple[str, tuple[float, str]], list[Listing]] = {}
    for item in items:
        size = _size_signature(item.pack_size)
        if size is not None:
            by_exact.setdefault((normalize_name(item.item_name), size), []).append(item)
    for group in by_exact.values():
        for item in group[1:]:
            union(group[0].id, item.id)

    labels_path = Path(__file__).resolve().parents[2] / "data/labels/match_pairs.csv"
    if labels_path.is_file():
        by_id = {item.id: item for item in items}
        with labels_path.open(encoding="utf-8", newline="") as source:
            for row in csv.DictReader(source):
                if (
                    row.get("label", "").strip() == "1"
                    and row.get("id_a") in by_id
                    and row.get("id_b") in by_id
                ):
                    union(row["id_a"], row["id_b"])

    threshold_path = Path(__file__).resolve().parents[3] / "notebooks/output/match_threshold.json"
    if threshold_path.is_file():
        try:
            artifact = json.loads(threshold_path.read_text(encoding="utf-8"))
            # Synthetic scores validate the notebook pipeline only. They cannot
            # broaden production grouping before the human pair labels are reviewed.
            threshold = (
                float(artifact["threshold"])
                if artifact.get("source") == "human_review"
                else None
            )
        except (OSError, ValueError, KeyError, TypeError):
            threshold = None
        if threshold is not None:
            for index, left in enumerate(items):
                left_size = _size_signature(left.pack_size)
                if left_size is None:
                    continue
                for right in items[index + 1:]:
                    if left.supermarket == right.supermarket:
                        continue
                    if left_size == _size_signature(right.pack_size) and _match_score(
                        left.item_name, right.item_name
                    ) >= threshold:
                        union(left.id, right.id)

    members: dict[str, list[Listing]] = {}
    for item in items:
        members.setdefault(find(item.id), []).append(item)
    result = []
    for group in members.values():
        stores = {item.supermarket for item in group}
        if len(stores) < 2:
            continue
        selected_by_store = [
            min(
                (item for item in group if item.supermarket == store),
                key=lambda item: item.price_kes,
            )
            for store in sorted(stores)
        ]
        identity = "|".join(sorted(item.id for item in selected_by_store))
        group_id = "match-" + hashlib.sha256(identity.encode()).hexdigest()[:16]
        label = min((item.item_name for item in selected_by_store), key=len)
        result.append(ComparableGroup(group_id, label, "same product", tuple(selected_by_store)))
    return result


def _staple_groups(items: tuple[Listing, ...]) -> list[ComparableGroup]:
    config = Path(__file__).resolve().parents[2] / "data/listings/staple_groups.json"
    if not config.is_file():
        return []
    definitions = json.loads(config.read_text(encoding="utf-8"))
    result = []
    for definition in definitions:
        pattern = re.compile(definition["name_regex"], re.IGNORECASE)
        expected = (float(definition["quantity"]), definition["unit"])
        by_store: dict[str, Listing] = {}
        for item in items:
            if not item.grocery or not pattern.search(item.item_name):
                continue
            if _size_signature(item.pack_size) != expected:
                continue
            current = by_store.get(item.supermarket)
            if current is None or item.price_kes < current.price_kes:
                by_store[item.supermarket] = item
        result.append(ComparableGroup(
            definition["id"], definition["label"], "staple substitute", tuple(
                by_store[store] for store in sorted(by_store)
            ),
        ))
    return result


@lru_cache(maxsize=1)
def get_comparable_groups() -> tuple[ComparableGroup, ...]:
    listings = get_listings()
    combined = _groups_from_matches(listings) + _staple_groups(listings)
    unique: dict[str, ComparableGroup] = {group.id: group for group in combined}
    return tuple(unique.values())


def get_comparable_group(group_id: str) -> ComparableGroup | None:
    return next((group for group in get_comparable_groups() if group.id == group_id), None)


def search_group(query: str) -> list[ComparableGroup]:
    needle = query.casefold()
    return [group for group in get_comparable_groups() if needle in group.label.casefold()]
