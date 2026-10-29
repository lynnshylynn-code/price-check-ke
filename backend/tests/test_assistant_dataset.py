import csv
import json
import sys
from collections import Counter
from math import floor
from pathlib import Path
from random import Random
from statistics import median

ROOT = Path(__file__).parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from build_assistant_dataset import (  # noqa: E402
    MAX_FILLINGS_PER_TEMPLATE,
    MIN_FILLINGS_PER_TEMPLATE,
    SEED,
    SPLIT_DIR,
    SPLIT_SEED,
    TEMPLATES_PATH,
    balance_training_rows,
    expand_templates,
    families_by_intent,
    remove_training_leaks,
    split_families,
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


def test_training_rows_are_capped_by_intent_and_sampled_across_families():
    rows = expand_templates(Random(SEED))
    train, _validation, _test = split_families(Random(SPLIT_SEED))
    first, dropped = balance_training_rows(rows, train, Random(SEED + 2))
    second, second_dropped = balance_training_rows(rows, train, Random(SEED + 2))
    assert first == second
    assert dropped == second_dropped
    raw_counts = Counter(row["intent"] for row in rows if row["family_id"] in train)
    cap = floor(median(raw_counts.values()) * 1.25)
    counts = Counter(row["intent"] for row in first)
    assert all(count <= cap for count in counts.values())
    for intent, families in families_by_intent(TEMPLATES_PATH).items():
        included = Counter(
            row["family_id"] for row in first if row["intent"] == intent
        )
        assert set(included) == set(families) & train
        if raw_counts[intent] > cap:
            assert max(included.values()) - min(included.values()) <= 1


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

