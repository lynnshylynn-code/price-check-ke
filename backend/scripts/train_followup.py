"""Train a local classifier for synthetic assistant follow-up messages."""

from __future__ import annotations

import csv
import hashlib
import json
import re
import sys
import time
from datetime import date
from pathlib import Path
from typing import Any

import joblib
import numpy as np
import sklearn
from sklearn.calibration import CalibratedClassifierCV
from sklearn.dummy import DummyClassifier
from sklearn.ensemble import RandomForestClassifier
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, f1_score, precision_recall_fscore_support
from sklearn.pipeline import FeatureUnion, Pipeline
from sklearn.svm import LinearSVC

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data/assistant/followup_splits"
MODEL_DIR = ROOT / "models"
MIN_COVERAGE = 0.85
sys.path.insert(0, str(ROOT / "src"))


def read(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8", newline="") as source:
        return list(csv.DictReader(source))


def augment(question: str) -> str:
    from price_check_api.dialogue import _known_entities

    text = question.casefold()
    tags = []
    for slot, tag in (("store", "HAS_STORE"), ("product", "HAS_PRODUCT"),
                      ("county", "HAS_COUNTY")):
        if any(
            re.search(rf"(?<!\w){re.escape(value)}(?!\w)", text)
            for value in _known_entities()[slot]
        ):
            tags.append(tag)
    if re.search(r"\b20\d{2}\b", text):
        tags.append("HAS_YEAR")
    if len(text.split()) <= 5:
        tags.append("IS_SHORT")
    return text + " " + " ".join(tags)


def candidates() -> dict[str, Pipeline]:
    def pipeline(classifier: Any) -> Pipeline:
        features = FeatureUnion([
            ("word", TfidfVectorizer(ngram_range=(1, 2), min_df=1, sublinear_tf=True)),
            ("char", TfidfVectorizer(analyzer="char_wb", ngram_range=(3, 5), min_df=1)),
        ])
        return Pipeline([("features", features), ("classifier", classifier)])
    return {
        "LogisticRegression": pipeline(LogisticRegression(
            class_weight="balanced", max_iter=1200, random_state=42)),
        "CalibratedLinearSVC": pipeline(CalibratedClassifierCV(
            estimator=LinearSVC(class_weight="balanced", random_state=42), cv=3)),
        "RandomForest": pipeline(RandomForestClassifier(
            n_estimators=100, class_weight="balanced", random_state=42, n_jobs=1)),
        "DummyMostFrequent": pipeline(DummyClassifier(strategy="most_frequent")),
    }


def select_threshold(labels: list[str], classes: np.ndarray, probs: np.ndarray) -> float:
    confidence = probs.max(axis=1)
    predicted = classes[probs.argmax(axis=1)]
    thresholds = sorted(set([0.0, *map(float, confidence)]))
    eligible = []
    for threshold in thresholds:
        accepted = confidence >= threshold
        coverage = float(np.mean(accepted))
        if coverage >= MIN_COVERAGE:
            accuracy = float(accuracy_score(np.asarray(labels)[accepted], predicted[accepted]))
            eligible.append((accuracy, coverage, threshold))
    if eligible:
        chosen = max(eligible)[2]
        print(f"Validation abstain threshold: {chosen:.4f} (coverage rule >= {MIN_COVERAGE:.0%})")
        return chosen
    positive = [(float(np.mean(confidence >= t)), t) for t in thresholds if t > 0]
    if not positive:
        print("Warning: no positive threshold accepts validation rows; selecting 0.0 explicitly.")
        return 0.0
    coverage, chosen = max(positive)
    print(
        f"Warning: no threshold reaches {MIN_COVERAGE:.0%} coverage; "
        f"highest positive coverage={coverage:.4f}."
    )
    return chosen


def main() -> int:
    train, validation, test = (read(DATA / f"{name}_questions.csv")
                               for name in ("train", "validation", "test"))
    x_train = [augment(row["question"]) for row in train]
    y_train = [row["label"] for row in train]
    x_valid = [augment(row["question"]) for row in validation]
    y_valid = [row["label"] for row in validation]
    scores: dict[str, tuple[Pipeline, float, float]] = {}
    print("Follow-up model comparison (validation split):")
    print("  model | validation accuracy | validation macro-F1 | training seconds")
    for name, model in candidates().items():
        started = time.perf_counter()
        model.fit(x_train, y_train)
        elapsed = time.perf_counter() - started
        probabilities = model.predict_proba(x_valid)
        threshold = select_threshold(y_valid, np.asarray(model.classes_), probabilities)
        validation_predictions = model.predict(x_valid)
        validation_accuracy = float(accuracy_score(y_valid, validation_predictions))
        macro = float(
            f1_score(y_valid, validation_predictions, average="macro", zero_division=0)
        )
        scores[name] = (model, threshold, macro)
        print(
            f"  {name} | {validation_accuracy:.4f} | {macro:.4f} | {elapsed:.3f}"
        )
    name = max(scores, key=lambda candidate: scores[candidate][2])
    model, threshold, _ = scores[name]
    truth = [row["label"] for row in test]
    probs = model.predict_proba([augment(row["question"]) for row in test])
    classes = np.asarray(model.classes_)
    predictions = classes[probs.argmax(axis=1)].astype(str)
    predictions[probs.max(axis=1) < threshold] = "__abstain__"
    labels = sorted(set(truth))
    precision, recall, f1, support = precision_recall_fscore_support(
        truth, predictions, labels=labels, zero_division=0)
    print(f"Selected follow-up model: {name}; threshold={threshold:.4f}")
    print("Synthetic follow-up test:", {
        "accuracy": float(accuracy_score(truth, predictions)),
        "macro_f1": float(
            f1_score(truth, predictions, labels=labels, average="macro", zero_division=0)
        ),
    })
    per_label = {label: {"precision": float(precision[i]), "recall": float(recall[i]),
                         "f1": float(f1[i]), "support": int(support[i])}
                 for i, label in enumerate(labels)}
    for label, metrics in per_label.items():
        print(f"  {label}: precision={metrics['precision']:.4f}, recall={metrics['recall']:.4f}, "
              f"F1={metrics['f1']:.4f}, support={metrics['support']}")
    MODEL_DIR.mkdir(parents=True, exist_ok=True)
    training_path = DATA / "train_questions.csv"
    metadata = {
        "model_name": name,
        "training_date": date.today().isoformat(),
        "sklearn_version": sklearn.__version__,
        "training_data_sha256": hashlib.sha256(training_path.read_bytes()).hexdigest(),
        "training_rows": len(train),
        "validation_rows": len(validation),
        "synthetic_test_rows": len(test),
        "confidence_threshold": threshold,
        "metrics": {"synthetic_test": {"accuracy": float(accuracy_score(truth, predictions)),
                     "macro_f1": float(f1_score(truth, predictions, labels=labels,
                                                 average="macro", zero_division=0)),
                     "per_label": per_label}},
    }
    joblib.dump(model, MODEL_DIR / "followup_pipeline.joblib")
    (MODEL_DIR / "followup_metadata.json").write_text(
        json.dumps(metadata, indent=2), encoding="utf-8"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
