"""Command-line copy of notebooks/assistant_intent_crisp_dm.ipynb.

The CRISP-DM notebook is the main training path; this script keeps a repeatable
command-line training path with the same features, threshold selection, and
artifact format.
"""

from __future__ import annotations

import csv
import hashlib
import json
from datetime import date
from pathlib import Path
from typing import Any

import joblib
import numpy as np
import sklearn
from sklearn.calibration import CalibratedClassifierCV
from sklearn.dummy import DummyClassifier
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    accuracy_score,
    confusion_matrix,
    f1_score,
    precision_recall_fscore_support,
)
from sklearn.naive_bayes import MultinomialNB
from sklearn.pipeline import FeatureUnion, Pipeline
from sklearn.svm import LinearSVC

ROOT = Path(__file__).resolve().parents[1]
ASSISTANT_DIR = ROOT / "data/assistant"
SPLIT_DIR = ASSISTANT_DIR / "splits"
MODEL_DIR = ROOT / "models"
TRAIN_FILE = SPLIT_DIR / "train_questions.csv"
VALIDATION_FILE = SPLIT_DIR / "validation_questions.csv"
TEST_FILE = SPLIT_DIR / "test_questions.csv"
HELDOUT_FILE = ASSISTANT_DIR / "heldout_test_questions.csv"
MODEL_FILE = MODEL_DIR / "intent_pipeline.joblib"
METADATA_FILE = MODEL_DIR / "metadata.json"
MIN_VALIDATION_COVERAGE = 0.70
ABSTAIN = "__abstain__"


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8", newline="") as source:
        return list(csv.DictReader(source))


def feature_union() -> FeatureUnion:
    return FeatureUnion(
        [
            (
                "word",
                TfidfVectorizer(ngram_range=(1, 2), min_df=1, sublinear_tf=True),
            ),
            (
                "character",
                TfidfVectorizer(
                    analyzer="char_wb", ngram_range=(3, 5), min_df=1, sublinear_tf=True,
                ),
            ),
        ]
    )


def candidates() -> dict[str, Pipeline]:
    return {
        "LogisticRegression": Pipeline(
            [
                ("features", feature_union()),
                ("classifier", LogisticRegression(C=3.0, max_iter=1500, random_state=42)),
            ]
        ),
        "CalibratedLinearSVC": Pipeline(
            [
                ("features", feature_union()),
                (
                    "classifier",
                    CalibratedClassifierCV(
                        estimator=LinearSVC(C=1.0, random_state=42),
                        method="sigmoid",
                        cv=3,
                    ),
                ),
            ]
        ),
        "MultinomialNB": Pipeline(
            [
                ("features", feature_union()),
                ("classifier", MultinomialNB(alpha=0.2)),
            ]
        ),
        "DummyMostFrequent": Pipeline(
            [
                ("features", feature_union()),
                ("classifier", DummyClassifier(strategy="most_frequent")),
            ]
        ),
    }


def probabilities(model: Pipeline, questions: list[str]) -> tuple[np.ndarray, np.ndarray]:
    values = model.predict_proba(questions)
    return np.asarray(model.classes_), values


def choose_threshold(
    labels: list[str], model_classes: np.ndarray, probs: np.ndarray,
) -> tuple[float, dict[str, float]]:
    confidence = probs.max(axis=1)
    indexes = probs.argmax(axis=1)
    candidates = np.unique(np.concatenate(([0.0], confidence)))
    best: tuple[float, float, float] | None = None
    best_result: dict[str, float] = {}
    best_threshold = 0.0
    for threshold in candidates:
        predictions = np.where(confidence >= threshold, model_classes[indexes], ABSTAIN)
        coverage = float(np.mean(predictions != ABSTAIN))
        if coverage < MIN_VALIDATION_COVERAGE:
            continue
        model_labels = sorted(set(labels))
        class_scores = f1_score(
            labels,
            predictions,
            labels=model_labels + [ABSTAIN],
            average=None,
            zero_division=0,
        )
        macro = float(np.mean(class_scores[: len(model_labels)]))
        result = (macro, coverage, -float(threshold))
        if best is None or result > best:
            best = result
            best_threshold = float(threshold)
            accepted = predictions != ABSTAIN
            best_result = {
                "macro_f1_with_abstentions": macro,
                "accepted_accuracy": float(accuracy_score(
                    np.asarray(labels)[accepted], predictions[accepted]
                )) if np.any(accepted) else 0.0,
                "coverage": coverage,
            }
    return best_threshold, best_result


def evaluate(
    name: str,
    model: Pipeline,
    rows: list[dict[str, str]],
    threshold: float | None,
) -> dict[str, Any]:
    questions = [row["question"] for row in rows]
    truth = np.asarray([row["intent"] for row in rows])
    classes, probs = probabilities(model, questions)
    confidence = probs.max(axis=1)
    prediction = classes[probs.argmax(axis=1)].astype(str)
    if threshold is not None:
        prediction[confidence < threshold] = ABSTAIN

    intent_labels = sorted(set(truth) | set(classes.astype(str)))
    all_labels = intent_labels + [ABSTAIN]
    precision, recall, f1, support = precision_recall_fscore_support(
        truth, prediction, labels=all_labels, zero_division=0,
    )
    macro = float(np.mean(f1[: len(intent_labels)]))
    metrics = {
        "accuracy": float(accuracy_score(truth, prediction)),
        "macro_f1": macro,
        "rows": len(rows),
        "gold_support_by_intent": {
            label: int(count)
            for label, count in zip(all_labels, support, strict=True)
        },
        "coverage": float(np.mean(prediction != ABSTAIN)),
        "abstained": int(np.sum(prediction == ABSTAIN)),
        "per_intent": {
            label: {
                "precision": float(precision[index]),
                "recall": float(recall[index]),
                "f1": float(f1[index]),
                "support": int(support[index]),
            }
            for index, label in enumerate(all_labels)
        },
        "confusion_labels": all_labels,
        "confusion_matrix": confusion_matrix(truth, prediction, labels=all_labels).tolist(),
    }
    print(
        f"\n{name}: rows={metrics['rows']} | accuracy={metrics['accuracy']:.4f} "
        f"| macro-F1={macro:.4f} | coverage={metrics['coverage']:.4f} "
        f"| abstained={metrics['abstained']}"
    )
    print("Per-intent precision / recall / F1 / support:")
    for intent in intent_labels:
        row = metrics["per_intent"][intent]
        print(
            f"  {intent}: {row['precision']:.4f} / {row['recall']:.4f} "
            f"/ {row['f1']:.4f} / {row['support']}"
        )
    print("Confusion matrix labels:", all_labels)
    print(np.asarray(metrics["confusion_matrix"]))
    return metrics


def heldout_by_source(rows: list[dict[str, str]]) -> dict[str, list[dict[str, str]]]:
    groups: dict[str, list[dict[str, str]]] = {}
    for row in rows:
        source = row.get("source", "unspecified")
        groups.setdefault(source, []).append(
            {**row, "intent": row["expected_intent"]}
        )
    return groups


def main() -> None:
    train = read_csv(TRAIN_FILE)
    validation = read_csv(VALIDATION_FILE)
    synthetic_test = read_csv(TEST_FILE)
    heldout_rows = read_csv(HELDOUT_FILE)
    if any(row.get("source") != "ai_written" for row in heldout_rows):
        raise ValueError("Expected heldout_test_questions.csv to contain only AI-written rows")

    x_train = [row["question"] for row in train]
    y_train = [row["intent"] for row in train]
    x_validation = [row["question"] for row in validation]
    y_validation = [row["intent"] for row in validation]
    fitted: dict[str, tuple[Pipeline, float, dict[str, float]]] = {}
    print("Validation model selection (synthetic validation split only):")
    for name, model in candidates().items():
        model.fit(x_train, y_train)
        classes, probs = probabilities(model, x_validation)
        threshold, validation_metrics = choose_threshold(y_validation, classes, probs)
        fitted[name] = (model, threshold, validation_metrics)
        print(
            f"  {name}: threshold={threshold:.4f}; "
            f"macro-F1={validation_metrics['macro_f1_with_abstentions']:.4f}; "
            f"accepted accuracy={validation_metrics['accepted_accuracy']:.4f}; "
            f"coverage={validation_metrics['coverage']:.4f}"
        )

    chosen_name = max(
        fitted,
        key=lambda name: (
            fitted[name][2]["macro_f1_with_abstentions"],
            fitted[name][2]["accepted_accuracy"],
            fitted[name][2]["coverage"],
        ),
    )
    chosen_model, threshold, validation_metrics = fitted[chosen_name]
    print(f"Selected model: {chosen_name}; confidence threshold={threshold:.4f}")

    dummy = candidates()["DummyMostFrequent"]
    dummy.fit(x_train, y_train)
    synthetic_result = evaluate(
        "Synthetic test split (generated questions)",
        chosen_model,
        synthetic_test,
        threshold,
    )
    synthetic_dummy = evaluate(
        "Synthetic test split baseline (DummyClassifier)", dummy, synthetic_test, None
    )
    heldout_metrics = {}
    heldout_dummy = {}
    for source, rows in heldout_by_source(heldout_rows).items():
        title = "AI-written held-out set" if source == "ai_written" else f"Held-out set ({source})"
        heldout_metrics[source] = evaluate(title, chosen_model, rows, threshold)
        heldout_dummy[source] = evaluate(f"{title} baseline (DummyClassifier)", dummy, rows, None)

    training_hash = hashlib.sha256(TRAIN_FILE.read_bytes()).hexdigest()
    metrics = {
        "validation": validation_metrics,
        "synthetic_test": synthetic_result,
        "synthetic_test_dummy_baseline": synthetic_dummy,
        "heldout_by_source": heldout_metrics,
        "heldout_dummy_by_source": heldout_dummy,
    }
    metadata = {
        "model_name": chosen_name,
        "training_date": date.today().isoformat(),
        "sklearn_version": sklearn.__version__,
        "training_data_sha256": training_hash,
        "training_rows": len(train),
        "validation_rows": len(validation),
        "synthetic_test_rows": len(synthetic_test),
        "heldout_rows_by_source": {
            key: len(value) for key, value in heldout_by_source(heldout_rows).items()
        },
        "confidence_threshold": threshold,
        "minimum_validation_coverage": MIN_VALIDATION_COVERAGE,
        "metrics": metrics,
    }
    MODEL_DIR.mkdir(parents=True, exist_ok=True)
    joblib.dump(chosen_model, MODEL_FILE)
    METADATA_FILE.write_text(json.dumps(metadata, indent=2), encoding="utf-8")
    print(f"Saved model artifact: {MODEL_FILE.relative_to(ROOT)}")
    print(f"Saved model metadata: {METADATA_FILE.relative_to(ROOT)}")
    print(f"Training data SHA-256: {training_hash}")


if __name__ == "__main__":
    main()
