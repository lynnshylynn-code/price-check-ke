import csv
from pathlib import Path

LABELS = Path(__file__).parents[1] / "data/labels"


def test_suggestion_sheets_keep_human_labels_blank_and_include_hard_negatives():
    with (LABELS / "match_pairs.csv").open(encoding="utf-8", newline="") as source:
        pairs = list(csv.DictReader(source))
    with (LABELS / "category_sample.csv").open(encoding="utf-8", newline="") as source:
        categories = list(csv.DictReader(source))
    assert len(pairs) == len(categories) == 60
    assert all(not row["label"].strip() for row in pairs + categories)
    assert all(row["suggestion_confidence"] in {"high", "medium", "low"}
               for row in pairs + categories)
    assert any("sizes differ" in row["evidence"] for row in pairs)
