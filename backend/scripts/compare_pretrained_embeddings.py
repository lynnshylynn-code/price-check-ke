"""Optional local sentence-embedding comparison for intent classification."""

from __future__ import annotations

import argparse
import importlib.util
import json
from collections.abc import Sequence
from pathlib import Path

import joblib
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import f1_score

ROOT = Path(__file__).resolve().parents[1]
ASSISTANT_DIR = ROOT / "data/assistant"
MODEL_DIR = ROOT / "models"


def _macro_f1(model: object, questions: Sequence[str], labels: Sequence[str]) -> float:
    return float(f1_score(labels, model.predict(questions), average="macro", zero_division=0))


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--model",
        default="sentence-transformers/all-MiniLM-L6-v2",
        help="Sentence Transformers model identifier or local model directory.",
    )
    args = parser.parse_args(argv)
    if importlib.util.find_spec("sentence_transformers") is None:
        print(
            "Optional comparison not run: sentence-transformers is not installed. "
            "Install it in a separate environment to enable this comparison."
        )
        return 0

    import csv

    try:
        from sentence_transformers import SentenceTransformer
    except ImportError as error:
        print(f"Optional comparison unavailable: {error}")
        return 0

    def read_rows(path: Path) -> list[dict[str, str]]:
        with path.open(encoding="utf-8-sig", newline="") as source:
            return list(csv.DictReader(source))

    try:
        train = read_rows(ASSISTANT_DIR / "splits/train_questions.csv")
        validation = read_rows(ASSISTANT_DIR / "splits/validation_questions.csv")
        test = read_rows(ASSISTANT_DIR / "splits/test_questions.csv")
        heldout = read_rows(ASSISTANT_DIR / "heldout_test_questions.csv")
        selected_name = json.loads((MODEL_DIR / "metadata.json").read_text(encoding="utf-8"))[
            "model_name"
        ]
        baseline_path = MODEL_DIR / "intent_pipeline.joblib"
        if baseline_path.is_file():
            baseline = joblib.load(baseline_path)
        else:
            from train_assistant import candidates

            baseline = candidates()[selected_name]
            baseline.fit(
                [row["question"] for row in train],
                [row["intent"] for row in train],
            )
        encoder = SentenceTransformer(args.model)
    except (OSError, KeyError, ValueError, ImportError) as error:
        print(f"Optional comparison could not load its local data/model: {error}")
        return 1

    x_train = encoder.encode(
        [row["question"] for row in train], convert_to_numpy=True, show_progress_bar=True
    )
    classifier = LogisticRegression(max_iter=1500, class_weight="balanced", random_state=42)
    classifier.fit(x_train, [row["intent"] for row in train])
    splits = {
        "validation": validation,
        "synthetic_test": test,
        "ai_written_heldout": [
            {**row, "intent": row["expected_intent"]}
            for row in heldout
            if row.get("source") == "ai_written"
        ],
    }
    print("Macro-F1 comparison without abstention (same evaluation splits):")
    for name, rows in splits.items():
        if not rows:
            print(f"{name}: no rows")
            continue
        questions = [row["question"] for row in rows]
        labels = [row.get("intent") or row["expected_intent"] for row in rows]
        baseline_score = _macro_f1(baseline, questions, labels)
        embeddings = encoder.encode(questions, convert_to_numpy=True, show_progress_bar=False)
        embedding_score = _macro_f1(classifier, embeddings, labels)
        print(
            f"{name}: TF-IDF={baseline_score:.4f}; "
            f"pretrained embeddings={embedding_score:.4f}"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
