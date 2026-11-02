from __future__ import annotations

import csv
import json
from collections import defaultdict
from math import floor
from pathlib import Path
from statistics import median

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data/assistant"
SPLITS = DATA / "followup_splits"


def test_followup_templates_have_eight_families_and_three_styles_per_label() -> None:
    families: dict[str, dict[str, set[str]]] = defaultdict(lambda: defaultdict(set))
    with (DATA / "followup_templates.csv").open(encoding="utf-8", newline="") as source:
        for row in csv.DictReader(source):
            families[row["label"]][row["family_id"]].add(row["style"])
    assert len(families) == 9
    for label, label_families in families.items():
        assert len(label_families) >= 8, label
        assert all(len(styles) >= 3 for styles in label_families.values()), label


def test_followup_splits_are_family_disjoint_and_cover_every_label() -> None:
    labels_by_split = {}
    families_by_split = {}
    for name in ("train", "validation", "test"):
        path = SPLITS / f"{name}_questions.csv"
        with path.open(encoding="utf-8", newline="") as source:
            rows = list(csv.DictReader(source))
        labels_by_split[name] = {row["label"] for row in rows}
        families_by_split[name] = {row["family_id"] for row in rows}
    assert labels_by_split["train"] == labels_by_split["validation"] == labels_by_split["test"]
    assert not families_by_split["train"] & families_by_split["validation"]
    assert not families_by_split["train"] & families_by_split["test"]
    assert not families_by_split["validation"] & families_by_split["test"]


def test_followup_training_rows_obey_the_median_cap_and_floor() -> None:
    with (SPLITS / "train_questions.csv").open(encoding="utf-8", newline="") as source:
        rows = list(csv.DictReader(source))
    counts: dict[str, int] = defaultdict(int)
    for row in rows:
        counts[row["label"]] += 1
    middle = median(counts.values())
    assert max(counts.values()) <= floor(middle * 1.25)
    assert min(counts.values()) >= floor(middle * 0.70)


def test_dialogue_evaluation_file_is_ai_written_and_has_long_conversations() -> None:
    payload = json.loads((DATA / "dialogues_eval.json").read_text(encoding="utf-8"))
    assert payload["source"] == "ai_written"
    assert len(payload["dialogues"]) >= 25
    assert all(3 <= len(dialogue["turns"]) <= 6 for dialogue in payload["dialogues"])
    assert all("CHECKS" in turn for dialogue in payload["dialogues"] for turn in dialogue["turns"])
