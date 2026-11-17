import sys
from pathlib import Path

import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import Pipeline

ROOT = Path(__file__).parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "scripts"))
from train_assistant import (  # noqa: E402
    MIN_VALIDATION_COVERAGE,
    candidates,
    choose_intent_threshold,
    choose_threshold,
    cross_validate_candidates,
    evaluate,
    roc_auc_report,
)

from price_check_api.assistant_model import load_assistant_model  # noqa: E402


def test_validation_threshold_keeps_required_coverage_and_explains_zero(capsys):
    labels = ["cheapest_item", "out_of_scope", "cheapest_item", "out_of_scope"]
    classes = np.asarray(["cheapest_item", "out_of_scope"])
    probabilities = np.asarray(
        [[0.9, 0.1], [0.45, 0.55], [0.65, 0.35], [0.2, 0.8]],
    )
    threshold, metrics = choose_threshold(labels, classes, probabilities)
    assert 0 <= threshold <= 1
    assert metrics["coverage"] >= MIN_VALIDATION_COVERAGE
    assert set(metrics) == {"macro_f1_with_abstentions", "accepted_accuracy", "coverage"}
    if threshold == 0.0:
        assert "maximized validation macro-F1 with abstentions" in capsys.readouterr().out


def test_validation_threshold_maximizes_macro_f1_at_required_coverage():
    # 9 confident "a", 9 confident "b", then two low-confidence predictions that are wrong.
    labels = ["a"] * 9 + ["b"] * 9 + ["b", "a"]
    classes = np.asarray(["a", "b"])
    probabilities = np.asarray(
        [[0.9, 0.1]] * 9
        + [[0.1, 0.9]] * 9
        + [[0.51, 0.49], [0.49, 0.51]]
    )
    threshold, metrics = choose_threshold(labels, classes, probabilities)
    assert threshold > 0.5
    assert metrics["coverage"] >= MIN_VALIDATION_COVERAGE
    assert metrics["coverage"] == 0.9
    assert metrics["accepted_accuracy"] == 1.0


def test_validation_threshold_prioritizes_weak_class_recall_over_accepted_accuracy():
    labels = ["a"] * 90 + ["b"] * 5 + ["c"] * 5
    classes = np.asarray(["a", "b", "c"])
    probabilities = np.asarray(
        [[0.99, 0.005, 0.005]] * 90
        + [[0.005, 0.55, 0.445]] * 4
        + [[0.6, 0.39, 0.01]]
        + [[0.005, 0.005, 0.99]] * 5
    )

    threshold, metrics = choose_threshold(labels, classes, probabilities)

    assert threshold == 0.55
    assert metrics["coverage"] == 1.0
    assert metrics["accepted_accuracy"] == 0.99
    assert metrics["macro_f1_with_abstentions"] > 0.95


def test_validation_threshold_warns_when_no_candidate_meets_coverage(monkeypatch, capsys):
    import train_assistant

    monkeypatch.setattr(train_assistant, "MIN_VALIDATION_COVERAGE", 1.01)
    labels = ["a", "b"]
    classes = np.asarray(["a", "b"])
    probabilities = np.asarray([[0.8, 0.2], [0.2, 0.8]])
    threshold, metrics = choose_threshold(labels, classes, probabilities)
    assert threshold > 0.0
    assert metrics["coverage"] == 1.0
    assert "Warning: no confidence threshold reaches" in capsys.readouterr().out


def test_intent_threshold_meets_precision_target_without_breaking_coverage():
    labels = ["compare_stores"] * 4 + ["price_at_store"] * 34
    classes = np.asarray(["compare_stores", "price_at_store"])
    compare_confidence = [0.95, 0.9, 0.8, 0.7, 0.85, 0.75, 0.65, 0.55]
    probabilities = np.asarray(
        [[confidence, 1 - confidence] for confidence in compare_confidence]
        + [[0.1, 0.9]] * 30
    )

    threshold, metrics = choose_intent_threshold(
        labels, classes, probabilities, 0.5, "compare_stores", 0.75
    )

    assert threshold == 0.8
    assert metrics["precision"] == 0.75
    assert metrics["recall"] == 0.75
    assert metrics["coverage"] >= MIN_VALIDATION_COVERAGE


def test_intent_threshold_falls_back_when_precision_target_is_unreachable():
    labels = ["compare_stores", "price_at_store"]
    classes = np.asarray(["compare_stores", "price_at_store"])
    probabilities = np.asarray([[0.7, 0.3], [0.8, 0.2]])

    threshold, metrics = choose_intent_threshold(
        labels, classes, probabilities, 0.5, "compare_stores", 0.9
    )

    assert threshold == 0.5
    assert metrics["precision"] == 0.5


def test_evaluation_applies_intent_specific_abstention_threshold():
    class FixedPipeline:
        classes_ = np.asarray(["compare_stores", "price_at_store"])

        def predict_proba(self, questions: list[str]) -> np.ndarray:
            assert len(questions) == 3
            return np.asarray([[0.9, 0.1], [0.7, 0.3], [0.1, 0.9]])

    rows = [
        {"question": "compare stores A and B", "intent": "compare_stores"},
        {"question": "compare stores C and D", "intent": "compare_stores"},
        {"question": "price at store A", "intent": "price_at_store"},
    ]

    metrics = evaluate(
        "threshold regression",
        FixedPipeline(),
        rows,
        0.5,
        {"compare_stores": 0.8},
    )

    assert metrics["coverage"] == 2 / 3
    assert metrics["per_intent"]["compare_stores"]["recall"] == 0.5


def test_model_loader_reports_missing_artifacts_clearly(tmp_path):
    state = load_assistant_model(tmp_path)
    assert state.pipeline is None
    assert "model is unavailable" in state.error
    assert "train_assistant.py" in state.error


def test_linear_candidates_use_balanced_class_weights():
    models = candidates()
    assert models["LogisticRegression"].named_steps["classifier"].class_weight == "balanced"
    calibrated = models["CalibratedLinearSVC"].named_steps["classifier"]
    assert calibrated.estimator.class_weight == "balanced"


def test_grouped_stratified_cross_validation_returns_five_fold_summary():
    questions = [f"apple item {index}" for index in range(5)] + [
        f"banana item {index}" for index in range(5)
    ]
    labels = ["apple"] * 5 + ["banana"] * 5
    groups = [f"apple-{index}" for index in range(5)] + [
        f"banana-{index}" for index in range(5)
    ]
    model = Pipeline(
        [
            ("features", TfidfVectorizer()),
            ("classifier", LogisticRegression(random_state=42)),
        ]
    )

    result = cross_validate_candidates(
        questions,
        labels,
        groups,
        {"small-model": model},
    )["small-model"]

    assert len(result["fold_scores"]) == 5
    assert 0 <= result["macro_f1_mean"] <= 1
    assert result["macro_f1_std"] >= 0


def test_roc_auc_is_reported_per_intent_and_macro():
    class FixedPipeline:
        classes_ = np.asarray(["apple", "banana"])

        def predict_proba(self, questions: list[str]) -> np.ndarray:
            return np.asarray(
                [[0.9, 0.1], [0.8, 0.2], [0.2, 0.8], [0.1, 0.9]]
            )[: len(questions)]

    rows = [
        {"question": "apple one", "intent": "apple"},
        {"question": "apple two", "intent": "apple"},
        {"question": "banana one", "intent": "banana"},
        {"question": "banana two", "intent": "banana"},
    ]

    result = roc_auc_report(FixedPipeline(), rows)

    assert result["macro_auc_ovr"] == 1
    assert result["per_intent_auc_ovr"] == {"apple": 1, "banana": 1}
