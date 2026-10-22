import csv
import sys
from pathlib import Path

LABELS = Path(__file__).parents[1] / "data/labels"
sys.path.insert(0, str(Path(__file__).parents[1] / "scripts"))
from label_status import cohen_kappa  # noqa: E402


def test_suggestion_sheets_keep_human_labels_blank_and_include_hard_negatives():
    with (LABELS / "match_pairs.csv").open(encoding="utf-8", newline="") as source:
        pairs = list(csv.DictReader(source))
    with (LABELS / "category_sample.csv").open(encoding="utf-8", newline="") as source:
        categories = list(csv.DictReader(source))
    assert len(pairs) == 72
    assert len(categories) == 60
    assert all(not row["label"].strip() for row in pairs + categories)
    assert all(row["suggestion_confidence"] in {"high", "medium", "low"}
               for row in pairs + categories)
    assert all(row["suggested_label"].strip() for row in pairs + categories)
    assert all(row["product_url_a"].startswith("https://")
               and row["product_url_b"].startswith("https://")
               for row in pairs)
    assert all(row["product_url"].startswith("https://") for row in categories)
    assert all(float(row["blocking_similarity"]) >= 0 for row in pairs)
    assert sum(row["suggested_label"] == "1" for row in pairs) == 6
    assert sum("Same leading brand token" in row["evidence"] for row in pairs) == 20


def test_label_status_kappa_handles_agreement_and_review_disagreement():
    assert cohen_kappa(["1", "0"], ["1", "0"]) == 1.0
    assert cohen_kappa(["1", "1"], ["0", "0"]) == 0.0
    assert cohen_kappa([], []) is None
