"""Expand synthetic assistant templates into a training CSV and family splits."""

from __future__ import annotations

import csv
import json
import random
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ASSISTANT_DIR = ROOT / "data" / "assistant"
TEMPLATES_PATH = ASSISTANT_DIR / "assistant_question_templates.csv"
SLOTS_PATH = ASSISTANT_DIR / "assistant_slot_values.csv"
OUTPUT_PATH = ASSISTANT_DIR / "assistant_training_questions.csv"
SPLIT_DIR = ASSISTANT_DIR / "splits"

SEED = 42
SPLIT_SEED = SEED + 1
MAX_FILLINGS_PER_TEMPLATE = 20
MIN_FILLINGS_PER_TEMPLATE = 15
NOISE_FRACTION = 0.20
PAIR_SLOTS = (("store", "store2"), ("county", "county2"), ("group", "group2"))

# Hold out whole families; targets tuned so each intent appears in every split.
VAL_FAMILY_COUNT = 8
TEST_FAMILY_COUNT = 12


def load_slots(path: Path) -> dict[str, list[dict[str, str]]]:
    slots: dict[str, list[dict[str, str]]] = defaultdict(list)
    with path.open(encoding="utf-8", newline="") as handle:
        for row in csv.DictReader(handle):
            slots[row["slot"]].append(row)
    return slots


def fill_template(
    template: str,
    slots: dict[str, list[dict[str, str]]],
    rng: random.Random,
) -> tuple[str, dict[str, str]]:
    chosen: dict[str, dict[str, str]] = {}
    for slot_name in sorted(set(re.findall(r"\{(\w+)\}", template))):
        if slot_name not in slots:
            raise KeyError(f"Missing slot values for {slot_name!r} in template {template!r}")
        chosen[slot_name] = rng.choice(slots[slot_name])
    for left, right in PAIR_SLOTS:
        if left in chosen and right in chosen:
            alternatives = [
                row for row in slots[right]
                if row["canonical"] != chosen[left]["canonical"]
            ]
            if not alternatives:
                raise ValueError(
                    f"No canonical alternative for paired slots {left!r}/{right!r}"
                )
            if chosen[left]["canonical"] == chosen[right]["canonical"]:
                chosen[right] = rng.choice(alternatives)
    question = template
    for slot_name, row in chosen.items():
        question = question.replace("{" + slot_name + "}", row["surface_form"])
    entities = {slot_name: row["canonical"] for slot_name, row in chosen.items()}
    return question, entities


def apply_character_noise(text: str, rng: random.Random) -> str:
    if len(text) < 4:
        return text.lower()
    chars = list(text)
    ops = rng.randint(1, max(1, len(chars) // 8))
    for _ in range(ops):
        idx = rng.randrange(len(chars))
        choice = rng.choice(("drop", "swap", "lower"))
        if choice == "drop" and len(chars) > 3:
            chars.pop(idx)
        elif choice == "swap" and idx + 1 < len(chars):
            chars[idx], chars[idx + 1] = chars[idx + 1], chars[idx]
        elif chars[idx].isalpha():
            chars[idx] = chars[idx].lower()
    noisy = "".join(chars)
    noisy = re.sub(r"\s+", " ", noisy).strip()
    return noisy


def expand_templates(rng: random.Random) -> list[dict[str, str]]:
    slots = load_slots(SLOTS_PATH)
    rows: list[dict[str, str]] = []
    with TEMPLATES_PATH.open(encoding="utf-8", newline="") as handle:
        for template_row in csv.DictReader(handle):
            fillings = rng.randint(MIN_FILLINGS_PER_TEMPLATE, MAX_FILLINGS_PER_TEMPLATE)
            for _ in range(fillings):
                question, entities = fill_template(template_row["template"], slots, rng)
                if rng.random() < NOISE_FRACTION:
                    question = apply_character_noise(question, rng)
                rows.append(
                    {
                        "question": question,
                        "intent": template_row["intent"],
                        "family_id": template_row["family_id"],
                        "style": template_row["style"],
                        "entities": json.dumps(entities, sort_keys=True),
                    }
                )
    return rows


def families_by_intent(templates_path: Path) -> dict[str, list[str]]:
    intent_families: dict[str, set[str]] = defaultdict(set)
    with templates_path.open(encoding="utf-8", newline="") as handle:
        for row in csv.DictReader(handle):
            intent_families[row["intent"]].add(row["family_id"])
    return {intent: sorted(families) for intent, families in intent_families.items()}


def split_families(rng: random.Random) -> tuple[set[str], set[str], set[str]]:
    intent_families = families_by_intent(TEMPLATES_PATH)
    all_families = sorted({family for families in intent_families.values() for family in families})
    val: set[str] = set()
    test: set[str] = set()

    for intent, families in sorted(intent_families.items()):
        shuffled = families[:]
        rng.shuffle(shuffled)
        if len(shuffled) < 3:
            raise ValueError(
                f"Intent {intent!r} has fewer than three families; cannot represent it "
                "in all splits."
            )
        val.add(shuffled[0])
        test.add(shuffled[1])

    remaining = [family for family in all_families if family not in val and family not in test]
    rng.shuffle(remaining)
    while len(val) < VAL_FAMILY_COUNT and remaining:
        val.add(remaining.pop())
    while len(test) < TEST_FAMILY_COUNT and remaining:
        test.add(remaining.pop())

    train = set(all_families) - val - test
    return train, val, test


def write_split_files(
    rows: list[dict[str, str]],
    train: set[str],
    val: set[str],
    test: set[str],
) -> None:
    SPLIT_DIR.mkdir(parents=True, exist_ok=True)
    splits = {"train": train, "validation": val, "test": test}
    for name, families in splits.items():
        path = SPLIT_DIR / f"{name}_families.txt"
        path.write_text("\n".join(sorted(families)) + "\n", encoding="utf-8")
        subset = [row for row in rows if row["family_id"] in families]
        out_csv = SPLIT_DIR / f"{name}_questions.csv"
        with out_csv.open("w", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(
                handle,
                fieldnames=["question", "intent", "family_id", "style", "entities"],
            )
            writer.writeheader()
            writer.writerows(subset)

    summary_lines = ["split,families,rows"]
    for name, families in splits.items():
        row_count = sum(1 for row in rows if row["family_id"] in families)
        summary_lines.append(f"{name},{len(families)},{row_count}")
        intent_counts = Counter(row["intent"] for row in rows if row["family_id"] in families)
        print(f"\n{name}: {len(families)} families, {row_count} rows")
        print("  intents:", dict(sorted(intent_counts.items())))
    (SPLIT_DIR / "split_summary.csv").write_text("\n".join(summary_lines) + "\n", encoding="utf-8")


def validate_split_invariants(
    rows: list[dict[str, str]],
    train: set[str],
    validation: set[str],
    test: set[str],
) -> None:
    split_sets = (train, validation, test)
    if train & validation or train & test or validation & test:
        raise ValueError("A family_id appears in more than one split")
    expected = {row["family_id"] for row in rows}
    if set.union(*split_sets) != expected:
        raise ValueError("Some training families are missing from the split lists")
    all_intents = {row["intent"] for row in rows}
    for name, families in zip(("train", "validation", "test"), split_sets, strict=True):
        found = {row["intent"] for row in rows if row["family_id"] in families}
        if found != all_intents:
            raise ValueError(f"Split {name!r} does not contain every intent")


def main() -> int:
    rng = random.Random(SEED)
    rows = expand_templates(rng)
    with OUTPUT_PATH.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=["question", "intent", "family_id", "style", "entities"],
        )
        writer.writeheader()
        writer.writerows(rows)

    train, val, test = split_families(random.Random(SPLIT_SEED))
    validate_split_invariants(rows, train, val, test)
    write_split_files(rows, train, val, test)
    print(f"\nWrote {len(rows)} synthetic rows to {OUTPUT_PATH}")
    print(f"Family split: train={len(train)} validation={len(val)} test={len(test)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
