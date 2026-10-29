"""Expand synthetic assistant templates into a training CSV and family splits."""

from __future__ import annotations

import csv
import json
import random
import re
import sys
from collections import Counter, defaultdict
from math import floor
from pathlib import Path
from statistics import median

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
        holdout_count = 2 if len(shuffled) >= 5 else 1
        val.update(shuffled[:holdout_count])
        test.update(shuffled[holdout_count : holdout_count * 2])

    train = set(all_families) - val - test
    return train, val, test


def balance_training_rows(
    rows: list[dict[str, str]], train_families: set[str], rng: random.Random
) -> tuple[list[dict[str, str]], int]:
    """Cap each intent at 1.25 times the median count, sampled evenly by family."""
    grouped: dict[str, dict[str, list[dict[str, str]]]] = defaultdict(
        lambda: defaultdict(list)
    )
    for row in rows:
        if row["family_id"] in train_families:
            grouped[row["intent"]][row["family_id"]].append(row)

    counts = [
        sum(len(family_rows) for family_rows in families.values())
        for families in grouped.values()
    ]
    if not counts:
        return [], 0
    cap = floor(median(counts) * 1.25)
    balanced: list[dict[str, str]] = []
    for families in grouped.values():
        family_ids = list(families)
        rng.shuffle(family_ids)
        for family_rows in families.values():
            rng.shuffle(family_rows)
        selected = 0
        while selected < cap:
            progressed = False
            for family_id in family_ids:
                available = families[family_id]
                if available:
                    balanced.append(available.pop())
                    selected += 1
                    progressed = True
                    if selected == cap:
                        break
            if not progressed:
                break
    original_count = sum(counts)
    return balanced, original_count - len(balanced)


def write_split_files(
    rows: list[dict[str, str]],
    train: set[str],
    val: set[str],
    test: set[str],
    training_rows: list[dict[str, str]],
) -> None:
    SPLIT_DIR.mkdir(parents=True, exist_ok=True)
    splits = {"train": train, "validation": val, "test": test}
    for name, families in splits.items():
        path = SPLIT_DIR / f"{name}_families.txt"
        path.write_text("\n".join(sorted(families)) + "\n", encoding="utf-8")
        source_rows = training_rows if name == "train" else rows
        subset = [row for row in source_rows if row["family_id"] in families]
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
        source_rows = training_rows if name == "train" else rows
        row_count = sum(1 for row in source_rows if row["family_id"] in families)
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


def normalize_question(question: str) -> str:
    return " ".join(re.findall(r"[a-z0-9]+", question.casefold()))


def _character_trigrams(question: str) -> set[str]:
    return {question[index : index + 3] for index in range(max(0, len(question) - 2))}


def heldout_questions() -> list[tuple[str, str]]:
    heldout: list[tuple[str, str]] = []
    for filename, provenance in (
        ("heldout_test_questions.csv", "AI-written held-out"),
        ("human_test_questions.csv", "human-written held-out"),
    ):
        path = ASSISTANT_DIR / filename
        if path.is_file():
            with path.open(encoding="utf-8", newline="") as handle:
                heldout.extend(
                    (row.get("question", ""), provenance)
                    for row in csv.DictReader(handle)
                    if row.get("question", "").strip()
                )
    return heldout


def _max_similarity(question: str, heldout_grams: list[tuple[set[str], str]]) -> float:
    grams = _character_trigrams(normalize_question(question))
    highest = 0.0
    for reference_grams, _provenance in heldout_grams:
        union = grams | reference_grams
        similarity = len(grams & reference_grams) / len(union) if union else 1.0
        highest = max(highest, similarity)
    return highest


def remove_training_leaks(
    rows: list[dict[str, str]], threshold: float = 0.85
) -> tuple[list[dict[str, str]], int, float, str | None]:
    heldout = heldout_questions()
    heldout_grams = [
        (_character_trigrams(normalize_question(question)), provenance)
        for question, provenance in heldout
    ]
    heldout_normalized = {normalize_question(question) for question, _ in heldout}
    kept: list[dict[str, str]] = []
    dropped = 0
    for row in rows:
        question = row["question"]
        normalized = normalize_question(question)
        too_similar = _max_similarity(question, heldout_grams) >= threshold
        if normalized in heldout_normalized or too_similar:
            dropped += 1
        else:
            kept.append(row)
    highest = 0.0
    closest_source = None
    for row in kept:
        grams = _character_trigrams(normalize_question(row["question"]))
        for reference_grams, provenance in heldout_grams:
            union = grams | reference_grams
            similarity = len(grams & reference_grams) / len(union) if union else 1.0
            if similarity > highest:
                highest = similarity
                closest_source = provenance
    return kept, dropped, highest, closest_source


def validate_heldout_separation(rows: list[dict[str, str]]) -> tuple[float, str | None]:
    """Reject normalized train/held-out duplicates and report the nearest text pair."""
    heldout = heldout_questions()
    heldout_normalized = {normalize_question(question) for question, _ in heldout}
    generated_normalized = {normalize_question(row["question"]) for row in rows}
    duplicates = generated_normalized & heldout_normalized
    if duplicates:
        raise ValueError(
            "Generated assistant questions overlap with a held-out set after normalization: "
            + ", ".join(sorted(duplicates)[:3])
        )

    highest_similarity = 0.0
    closest_source = None
    heldout_grams = [
        (_character_trigrams(normalize_question(question)), provenance)
        for question, provenance in heldout
    ]
    for row in rows:
        generated_grams = _character_trigrams(normalize_question(row["question"]))
        for reference_grams, provenance in heldout_grams:
            union = generated_grams | reference_grams
            similarity = len(generated_grams & reference_grams) / len(union) if union else 1.0
            if similarity > highest_similarity:
                highest_similarity = similarity
                closest_source = provenance
    return highest_similarity, closest_source


def main() -> int:
    rng = random.Random(SEED)
    rows = expand_templates(rng)
    train, val, test = split_families(random.Random(SPLIT_SEED))
    raw_train = [row for row in rows if row["family_id"] in train]
    leak_free_train, leakage_dropped, _raw_similarity, _raw_source = remove_training_leaks(
        raw_train
    )
    balanced_train, balance_dropped = balance_training_rows(
        leak_free_train, train, random.Random(SEED + 2)
    )
    clean_train, final_leaks, highest_similarity, closest_source = remove_training_leaks(
        balanced_train
    )
    leakage_dropped += final_leaks
    retained_rows = clean_train + [row for row in rows if row["family_id"] not in train]
    validate_heldout_separation(retained_rows)
    print(f"Training rows dropped by intent balance cap: {balance_dropped}")
    print(f"Training rows dropped for held-out similarity >= 0.85: {leakage_dropped}")
    print(
        "Highest normalized character-trigram Jaccard similarity in retained training rows: "
        f"{highest_similarity:.4f} ({closest_source or 'no held-out questions found'})."
    )
    with OUTPUT_PATH.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=["question", "intent", "family_id", "style", "entities"],
        )
        writer.writeheader()
        writer.writerows(retained_rows)

    validate_split_invariants(retained_rows, train, val, test)
    compare_families = {row["family_id"] for row in rows if row["intent"] == "compare_stores"}
    compare_coverage = {
        name: len(families & compare_families)
        for name, families in (("train", train), ("validation", val), ("test", test))
    }
    if any(count == 0 for count in compare_coverage.values()):
        raise ValueError("compare_stores families must occur in train, validation, and test.")
    print("compare_stores families by split:", compare_coverage)
    write_split_files(retained_rows, train, val, test, clean_train)
    print(f"\nWrote {len(retained_rows)} synthetic rows to {OUTPUT_PATH}")
    training_intent_counts = Counter(row["intent"] for row in leak_free_train)
    row_cap = floor(median(training_intent_counts.values()) * 1.25)
    print("Maximum training rows per intent:", row_cap)
    print(f"Family split: train={len(train)} validation={len(val)} test={len(test)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
