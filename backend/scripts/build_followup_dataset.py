"""Expand synthetic follow-up templates using family-isolated dialogue splits."""

from __future__ import annotations

import csv
import json
import random
import re
import sys
from collections import defaultdict
from math import floor
from statistics import median
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data/assistant"
TEMPLATES = DATA / "followup_templates.csv"
OUTPUT = DATA / "followup_questions.csv"
SPLITS = DATA / "followup_splits"
SEED = 118


def slots() -> dict[str, list[dict[str, str]]]:
    with (DATA / "assistant_slot_values.csv").open(encoding="utf-8", newline="") as source:
        values: dict[str, list[dict[str, str]]] = defaultdict(list)
        for row in csv.DictReader(source):
            values[row["slot"]].append(row)
    return values


def main() -> int:
    rng = random.Random(SEED)
    slot_values = slots()
    rows: list[dict[str, str]] = []
    with TEMPLATES.open(encoding="utf-8", newline="") as source:
        templates = list(csv.DictReader(source))
    by_label: dict[str, list[str]] = defaultdict(list)
    for item in templates:
        if item["family_id"] not in by_label[item["label"]]:
            by_label[item["label"]].append(item["family_id"])
    for label, families in by_label.items():
        if len(families) < 8:
            raise ValueError(f"{label} needs at least 8 families, found {len(families)}")
        styles = defaultdict(set)
        for item in templates:
            if item["label"] == label:
                styles[item["family_id"]].add(item["style"])
        if any(len(styles[family]) < 3 for family in families):
            raise ValueError(f"Each {label} family must contain at least three styles")

    dialogue_file = DATA / "dialogues_eval.json"
    heldout = []
    if dialogue_file.is_file():
        payload = json.loads(dialogue_file.read_text(encoding="utf-8"))
        heldout = [
            re.sub(r"[^a-z0-9]+", " ", turn["user"].casefold()).strip()
            for dialogue in payload.get("dialogues", [])
            for turn in dialogue.get("turns", [])
        ]
    heldout_sets = [
        {normalized[i : i + 3] for i in range(max(0, len(normalized) - 2))}
        for normalized in heldout
    ]
    dropped = 0
    highest_similarity = 0.0
    for item in templates:
        names = sorted(set(re.findall(r"\{(\w+)\}", item["template"])))
        for index in range(12):
            answer = item["template"]
            entities = {}
            for name in names:
                options = slot_values.get(name, [])
                if not options:
                    raise ValueError(f"Missing slot values for {name}")
                selected = rng.choice(options)
                answer = answer.replace("{" + name + "}", selected["surface_form"])
                entities[name] = selected["canonical"]
            normalized = re.sub(r"[^a-z0-9]+", " ", answer.casefold()).strip()
            grams = {normalized[i : i + 3] for i in range(max(0, len(normalized) - 2))}
            similarities = [
                len(grams & reference) / len(grams | reference) if grams | reference else 1.0
                for reference in heldout_sets
            ]
            similarity = max(similarities, default=0.0)
            if normalized in heldout or similarity >= 0.85:
                dropped += 1
                continue
            highest_similarity = max(highest_similarity, similarity)
            rows.append({
                "question": answer,
                "label": item["label"],
                "family_id": item["family_id"],
                "style": item["style"],
                "entities": json.dumps(entities, sort_keys=True),
            })

    label_families: dict[str, list[str]] = defaultdict(list)
    for item in templates:
        if item["family_id"] not in label_families[item["label"]]:
            label_families[item["label"]].append(item["family_id"])
    train_families: set[str] = set()
    val_families: set[str] = set()
    test_families: set[str] = set()
    for families in label_families.values():
        shuffled = sorted(families)
        rng.shuffle(shuffled)
        val_families.update(shuffled[:2])
        test_families.update(shuffled[2:4])
        train_families.update(shuffled[4:])
    splits = {"train": train_families, "validation": val_families, "test": test_families}
    if (
        train_families & val_families
        or train_families & test_families
        or val_families & test_families
    ):
        raise ValueError("A follow-up family leaked across splits")
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    for target, family_set in splits.items():
        subset = [row for row in rows if row["family_id"] in family_set]
        if target == "train" and subset:
            grouped: dict[str, dict[str, list[dict[str, str]]]] = defaultdict(
                lambda: defaultdict(list)
            )
            for row in subset:
                grouped[row["label"]][row["family_id"]].append(row)
            median_count = median(
                sum(len(items) for items in family_rows.values())
                for family_rows in grouped.values()
            )
            cap = floor(median_count * 1.25)
            minimum = floor(median_count * 0.70)
            subset = []
            for label, families in grouped.items():
                family_ids = list(families)
                rng.shuffle(family_ids)
                for family_rows in families.values():
                    rng.shuffle(family_rows)
                selected = 0
                target_rows = min(cap, sum(len(items) for items in families.values()))
                while selected < max(minimum, target_rows):
                    added = False
                    for family_id in family_ids:
                        if families[family_id]:
                            subset.append(families[family_id].pop())
                            selected += 1
                            added = True
                            if selected >= cap:
                                break
                    if not added:
                        break
                if selected < minimum:
                    raise ValueError(f"Could not meet the 70% median floor for {label}")
            print(
                f"Training median={median_count:g}; cap={cap}; minimum floor={minimum} rows."
            )
        path = SPLITS / f"{target}_questions.csv"
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("w", encoding="utf-8", newline="") as output:
            writer = csv.DictWriter(output, fieldnames=list(rows[0]))
            writer.writeheader()
            writer.writerows(subset)
        counts: dict[str, int] = defaultdict(int)
        for row in subset:
            counts[row["label"]] += 1
        if target == "train":
            print("Training per-label rows after seeded family-balanced cap:")
            for label in sorted(counts):
                print(f"  {label}: {counts[label]}")
        else:
            print(f"{target}: {dict(sorted(counts.items()))}")
    with OUTPUT.open("w", encoding="utf-8", newline="") as output:
        writer = csv.DictWriter(output, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    print(f"Follow-up rows dropped for dialogue leakage >= 0.85: {dropped}")
    print(f"Highest retained dialogue trigram similarity: {highest_similarity:.4f}")
    print(f"Generated follow-up rows: {len(rows)}; family splits are deterministic.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
