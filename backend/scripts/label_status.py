"""Summarize human-reviewed labels against AI suggestions (never labels data)."""

import csv
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FILES = ("match_pairs.csv", "category_sample.csv")


def cohen_kappa(suggestions: list[str], labels: list[str]) -> float | None:
    if not labels:
        return None
    categories = set(suggestions) | set(labels)
    observed = sum(a == b for a, b in zip(suggestions, labels, strict=True)) / len(labels)
    expected = sum(
        (suggestions.count(category) / len(labels))
        * (labels.count(category) / len(labels))
        for category in categories
    )
    return 1.0 if expected == 1.0 and observed == 1.0 else (
        0.0 if expected == 1.0 else (observed - expected) / (1 - expected)
    )


def main() -> None:
    for filename in FILES:
        path = ROOT / "data/labels" / filename
        with path.open(encoding="utf-8-sig", newline="") as source:
            rows = list(csv.DictReader(source))
        reviewed = [row for row in rows if row.get("label", "").strip()]
        disagreements = sum(
            row["label"].strip().casefold() != row.get("suggested_label", "").strip().casefold()
            for row in reviewed
        )
        print(f"{filename}: reviewed {len(reviewed)}/{len(rows)}")
        if not reviewed:
            print(f"labels not reviewed yet: edit backend/data/labels/{filename}")
            continue
        suggestions = [row.get("suggested_label", "").strip().casefold() for row in reviewed]
        labels = [row["label"].strip().casefold() for row in reviewed]
        agreement = 100 * (len(reviewed) - disagreements) / len(reviewed)
        kappa = cohen_kappa(suggestions, labels)
        print(f"Suggestion disagreements: {disagreements}")
        print(f"Percent agreement: {agreement:.1f}%")
        print(f"Cohen's kappa: {kappa:.4f}")


if __name__ == "__main__":
    main()
