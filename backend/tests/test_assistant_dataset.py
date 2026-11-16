import csv
import json
import re
import sys
from collections import Counter
from math import floor
from pathlib import Path
from random import Random
from statistics import median

ROOT = Path(__file__).parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from build_assistant_dataset import (  # noqa: E402
    CAP_MULTIPLIER,
    MAX_FILLINGS_PER_TEMPLATE,
    MIN_FILLINGS_PER_TEMPLATE,
    SEED,
    SPLIT_DIR,
    SPLIT_SEED,
    STRAY_PUNCTUATION_FRACTION,
    TEMPLATES_PATH,
    apply_stray_punctuation_noise,
    balance_training_rows,
    expand_templates,
    families_by_intent,
    remove_training_leaks,
    split_families,
    top_up_training_rows,
    validate_heldout_separation,
)

ASSISTANT_DATA = ROOT / "data/assistant"


def read_rows(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8", newline="") as source:
        return list(csv.DictReader(source))


def test_expansion_is_seeded_capped_and_respects_canonical_pairs():
    first = expand_templates(Random(SEED))
    second = expand_templates(Random(SEED))
    assert first == second
    template_count = len(read_rows(TEMPLATES_PATH))
    assert template_count * MIN_FILLINGS_PER_TEMPLATE <= len(first)
    assert len(first) <= template_count * MAX_FILLINGS_PER_TEMPLATE
    for row in first:
        entities = json.loads(row["entities"])
        for left, right in (("store", "store2"), ("county", "county2"), ("group", "group2")):
            if left in entities and right in entities:
                assert entities[left] != entities[right]


def test_written_splits_hold_out_whole_families_and_keep_every_intent():
    train, validation, test = split_families(Random(SPLIT_SEED))
    assert not (train & validation or train & test or validation & test)
    assert train | validation | test == {
        row["family_id"] for row in read_rows(TEMPLATES_PATH)
    }
    intents_by_split = {}
    for name in ("train", "validation", "test"):
        rows = read_rows(SPLIT_DIR / f"{name}_questions.csv")
        family_file = (SPLIT_DIR / f"{name}_families.txt").read_text(encoding="utf-8")
        families = set(family_file.splitlines())
        assert {row["family_id"] for row in rows} == families
        intents_by_split[name] = {row["intent"] for row in rows}
        assert len(rows) > 0
    assert intents_by_split["train"] == intents_by_split["validation"] == intents_by_split["test"]
    compare_families = {
        row["family_id"]
        for row in read_rows(TEMPLATES_PATH)
        if row["intent"] == "compare_stores"
    }
    assert train & compare_families
    assert validation & compare_families
    assert test & compare_families
    templates_by_intent = families_by_intent(TEMPLATES_PATH)
    for families in templates_by_intent.values():
        minimum = 2 if len(families) >= 5 else 1
        assert sum(family in validation for family in families) >= minimum
        assert sum(family in test for family in families) >= minimum


def test_train_only_families_preserve_existing_holdout_assignments(tmp_path, monkeypatch):
    import build_assistant_dataset as dataset_builder

    templates_path = tmp_path / "templates.csv"
    train_only_path = tmp_path / "train_only_families.txt"
    fields = ["template_id", "family_id", "intent", "style", "template", "slots"]
    baseline_rows = [
        {
            "template_id": f"T{index}",
            "family_id": f"intent_family_{index}",
            "intent": "sample_intent",
            "style": "formal",
            "template": f"Sample question {index}",
            "slots": "",
        }
        for index in range(5)
    ]

    def write_templates(rows):
        with templates_path.open("w", encoding="utf-8", newline="") as output:
            writer = csv.DictWriter(output, fieldnames=fields)
            writer.writeheader()
            writer.writerows(rows)

    write_templates(baseline_rows)
    monkeypatch.setattr(dataset_builder, "TEMPLATES_PATH", templates_path)
    monkeypatch.setattr(dataset_builder, "TRAIN_ONLY_FAMILIES_PATH", train_only_path)
    _train, validation, test = split_families(Random(SPLIT_SEED))

    new_training_family = {
        "template_id": "T6",
        "family_id": "additional_training_family",
        "intent": "sample_intent",
        "style": "formal",
        "template": "Another sample question",
        "slots": "",
    }
    write_templates([*baseline_rows, new_training_family])
    train_only_path.write_text("additional_training_family\n", encoding="utf-8")
    train_with_addition, validation_with_addition, test_with_addition = split_families(
        Random(SPLIT_SEED)
    )

    assert validation_with_addition == validation
    assert test_with_addition == test
    assert "additional_training_family" in train_with_addition


def test_training_rows_are_capped_by_intent_and_sampled_across_families():
    rows = expand_templates(Random(SEED))
    train, _validation, _test = split_families(Random(SPLIT_SEED))
    first, dropped = balance_training_rows(rows, train, Random(SEED + 2))
    second, second_dropped = balance_training_rows(rows, train, Random(SEED + 2))
    assert first == second
    assert dropped == second_dropped
    raw_counts = Counter(row["intent"] for row in rows if row["family_id"] in train)
    cap = floor(median(raw_counts.values()) * CAP_MULTIPLIER)
    counts = Counter(row["intent"] for row in first)
    assert all(count <= cap for count in counts.values())
    for intent, families in families_by_intent(TEMPLATES_PATH).items():
        included = Counter(
            row["family_id"] for row in first if row["intent"] == intent
        )
        assert set(included) == set(families) & train
        if raw_counts[intent] > cap:
            capacities = Counter(
                row["family_id"]
                for row in rows
                if row["intent"] == intent and row["family_id"] in train
            )
            highest_count = max(included.values())
            assert all(
                count == capacities[family_id]
                for family_id, count in included.items()
                if count < highest_count - 1
            )


def test_stray_punctuation_noise_is_seeded_and_applies_to_about_ten_percent():
    rows = [{"question": f"training question {index}"} for index in range(100)]
    first, first_count = apply_stray_punctuation_noise(rows, Random(SEED + 4))
    second, second_count = apply_stray_punctuation_noise(rows, Random(SEED + 4))

    assert first == second
    assert first_count == second_count == round(len(rows) * STRAY_PUNCTUATION_FRACTION)
    changed = [
        row["question"]
        for row, original in zip(first, rows, strict=True)
        if row["question"] != original["question"]
    ]
    assert len(changed) == first_count
    assert all(question[-1] in "'\"?!." for question in changed)


def test_training_rows_at_or_above_heldout_similarity_threshold_are_removed(tmp_path, monkeypatch):
    import build_assistant_dataset as dataset_builder

    (tmp_path / "heldout_test_questions.csv").write_text(
        "question,expected_intent,source\n"
        "the price of maize flour in Naivas,price_at_store,ai_written\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(dataset_builder, "ASSISTANT_DIR", tmp_path)
    examples = [
        {"question": "the price of maize flour in Naivas", "intent": "price_at_store"},
        {"question": "completely unrelated question about weather", "intent": "out_of_scope"},
    ]
    kept, dropped, highest, source = remove_training_leaks(examples)
    assert dropped == 1
    assert len(kept) == 1
    assert highest < 0.85
    assert source == "AI-written held-out"


def test_generated_questions_have_no_normalized_heldout_overlap():
    rows = expand_templates(Random(SEED))
    similarity, source = validate_heldout_separation(rows)
    assert 0 <= similarity <= 1
    assert source in {"AI-written held-out", "human-written held-out", None}


def test_ai_written_heldout_set_remains_separate():
    heldout = read_rows(ASSISTANT_DATA / "heldout_test_questions.csv")
    training = read_rows(ASSISTANT_DATA / "assistant_training_questions.csv")
    assert len(heldout) == 91
    assert Counter(row["source"] for row in heldout) == {"ai_written": 91}
    assert {row["question"] for row in heldout}.isdisjoint(
        row["question"] for row in training
    )


def test_discount_and_unit_price_template_families_were_appended_sequentially():
    rows = read_rows(TEMPLATES_PATH)
    appended = [
        row for row in rows
        if 229 <= int(row["template_id"][1:]) <= 252
        and row["family_id"] in {
            *(f"unit_price_{number:02d}" for number in range(9, 13)),
            *(f"biggest_discount_{number:02d}" for number in range(9, 13)),
        }
    ]

    assert [row["template_id"] for row in appended] == [
        f"T{number:03d}" for number in range(229, 253)
    ]
    assert {row["family_id"] for row in appended[:12]} == {
        f"unit_price_{number:02d}" for number in range(9, 13)
    }
    assert {row["family_id"] for row in appended[12:]} == {
        f"biggest_discount_{number:02d}" for number in range(9, 13)
    }
    for row in appended:
        slots = sorted(set(re.findall(r"\{(\w+)\}", row["template"])))
        assert row["slots"] == ",".join(slots)


def test_cheapest_and_discount_families_were_appended_sequentially():
    appended = [
        row for row in read_rows(TEMPLATES_PATH)
        if 253 <= int(row["template_id"][1:]) <= 276
        and row["family_id"] in {
            *(f"cheapest_item_{number:02d}" for number in range(9, 13)),
            *(f"biggest_discount_{number:02d}" for number in range(13, 17)),
        }
    ]

    assert [row["template_id"] for row in appended] == [
        f"T{number:03d}" for number in range(253, 277)
    ]
    assert {row["family_id"] for row in appended[:12]} == {
        f"cheapest_item_{number:02d}" for number in range(9, 13)
    }
    assert {row["family_id"] for row in appended[12:]} == {
        f"biggest_discount_{number:02d}" for number in range(13, 17)
    }
    for row in appended:
        slots = sorted(set(re.findall(r"\{(\w+)\}", row["template"])))
        assert row["slots"] == ",".join(slots)


def test_targeted_weak_intent_templates_stay_in_training_families():
    rows = [
        row for row in read_rows(TEMPLATES_PATH)
        if 277 <= int(row["template_id"][1:]) <= 303
    ]
    assert [row["template_id"] for row in rows] == [
        f"T{number:03d}" for number in range(277, 304)
    ]
    families = [
        "cheapest_item_09",
        "cheapest_item_10",
        "cheapest_item_12",
        "unit_price_09",
        "unit_price_10",
        "unit_price_11",
        "biggest_discount_13",
        "biggest_discount_15",
        "biggest_discount_16",
    ]
    assert [rows[index]["family_id"] for index in range(0, 27, 3)] == families
    train_families = set(
        (SPLIT_DIR / "train_families.txt").read_text(encoding="utf-8").splitlines()
    )
    assert set(families) <= train_families
    for row in rows:
        slots = sorted(set(re.findall(r"\{(\w+)\}", row["template"])))
        assert row["slots"] == ",".join(slots)


def test_underrepresented_training_intent_is_topped_up_deterministically():
    train, _validation, _test = split_families(Random(SPLIT_SEED))
    families = families_by_intent(TEMPLATES_PATH)
    rows = []
    for intent, intent_families in families.items():
        family_id = next(family for family in intent_families if family in train)
        samples = 1 if intent == "cheapest_item" else 10
        rows.extend(
            {
                "question": f"generated sample {intent} {index}",
                "intent": intent,
                "family_id": family_id,
                "style": "formal",
                "entities": "{}",
            }
            for index in range(samples)
        )

    first = top_up_training_rows(rows, train, Random(SEED + 3))
    second = top_up_training_rows(rows, train, Random(SEED + 3))
    augmented, added, _leaks_dropped, median_rows, minimum_rows = first
    supplements = augmented[len(rows) :]
    final_counts = Counter(row["intent"] for row in augmented)

    assert first == second
    assert added["cheapest_item"] == minimum_rows - 1
    assert minimum_rows == floor(median_rows * 0.70)
    assert all(count >= minimum_rows for count in final_counts.values())
    assert all(row["family_id"] in train for row in augmented)
    assert validate_heldout_separation(supplements)[0] < 0.85

