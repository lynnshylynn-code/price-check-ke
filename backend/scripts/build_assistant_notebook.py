# ruff: noqa: E501
"""Build and execute the Colab-friendly assistant intent CRISP-DM notebook."""

from __future__ import annotations

import base64
import contextlib
import hashlib
import io
import json
import os
import re
import traceback
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
DESTINATION = ROOT / "notebooks/assistant_intent_crisp_dm.ipynb"


def _cell_id(kind: str, index: int, source: str) -> str:
    digest = hashlib.sha1(source.encode("utf-8")).hexdigest()[:8]
    return f"{kind}-{index}-{digest}"


def markdown(index: int, source: str) -> dict[str, Any]:
    return {
        "cell_type": "markdown",
        "id": _cell_id("md", index, source),
        "metadata": {},
        "source": source.splitlines(keepends=True),
    }


def code(index: int, source: str) -> dict[str, Any]:
    return {
        "cell_type": "code",
        "execution_count": None,
        "id": _cell_id("code", index, source),
        "metadata": {},
        "outputs": [],
        "source": source.splitlines(keepends=True),
    }


CELLS = [
    code(0, """# Notebook path overrides (Colab or local environment).
import contextlib
import io
import os
import sys
from pathlib import Path

def find_repo_root(start=Path.cwd()):
    for candidate in (start, *start.parents):
        if (candidate / "backend/scripts/train_assistant.py").is_file():
            return candidate
    return None

ROOT = find_repo_root()
if ROOT is None:
    raise FileNotFoundError(
        "Clone the Price Check KE repository in Colab and set ROOT to that checkout, "
        "or upload the backend/ directory with scripts and data."
    )
DATA_DIR = Path(os.environ.get("ASSISTANT_DATA_DIR", ROOT / "backend/data/assistant")).expanduser()
MODEL_DIR = Path(os.environ.get("ASSISTANT_MODEL_DIR", ROOT / "backend/models")).expanduser()
if not DATA_DIR.is_dir():
    raise FileNotFoundError("Set ASSISTANT_DATA_DIR to backend/data/assistant (upload this folder in Colab).")
if str(ROOT / "backend/src") not in sys.path:
    sys.path.insert(0, str(ROOT / "backend/src"))
if str(ROOT / "backend/scripts") not in sys.path:
    sys.path.insert(0, str(ROOT / "backend/scripts"))
try:
    from IPython.display import display
except ImportError:
    def display(value):
        print(value)

print("Repository checkout found; assistant data folder:", DATA_DIR.name)
print("Colab: clone the repo then change directory to that checkout; alternatively upload backend/data/assistant and set ASSISTANT_DATA_DIR. The training script must also be present.")
"""),
    markdown(1, """# Assistant intent classifier: CRISP-DM training notebook

This is the main training path for the deterministic Price Check KE assistant. Run locally with the repository's Python environment or in Colab after cloning the repository. The command-line copy is `backend/scripts/train_assistant.py`; both paths reuse its feature and threshold functions and write the same artifact format.

The generated questions are **SYNTHETIC**: AI-written templates were expanded into controlled variants. They do not represent real user language. Every score and figure below is computed from the checked-in data when the notebook runs; no metric is typed in as a result.
"""),
    markdown(2, """## Business understanding

The assistant routes questions to deterministic lookups for eight intents: `cheapest_item`, `price_at_store`, `compare_stores`, `biggest_discount`, `unit_price`, `market_price`, `food_inflation`, and `out_of_scope`. It should abstain when the strongest class probability is below a threshold chosen on the validation split. An abstention is safer than presenting an unsupported answer. This classifier routes requests; it does not itself invent or calculate prices.
"""),
    markdown(3, """## Data understanding

The train, validation, and synthetic test CSVs were generated from AI-written templates. The separate held-out CSV is also AI-written and is not human evaluation. This inspection uses pandas to expose the row and column counts, intent/style mix, question lengths, repeated questions, family counts, and possible split leakage before model fitting.
"""),
    code(4, """import pandas as pd
import numpy as np
import matplotlib.pyplot as plt

SPLIT_DIR = DATA_DIR / "splits"
train_df = pd.read_csv(SPLIT_DIR / "train_questions.csv")
validation_df = pd.read_csv(SPLIT_DIR / "validation_questions.csv")
test_df = pd.read_csv(SPLIT_DIR / "test_questions.csv")
splits = {"train": train_df, "validation": validation_df, "synthetic_test": test_df}
shape_table = pd.DataFrame({name: {"rows": len(frame), "columns": len(frame.columns)} for name, frame in splits.items()}).T
display(shape_table)
display(pd.concat({name: frame["intent"].value_counts() for name, frame in splits.items()}, axis=1).fillna(0).astype(int))
style_counts = pd.concat({name: frame["style"].value_counts() for name, frame in splits.items()}, axis=1).fillna(0).astype(int)
display(style_counts)
for frame in splits.values():
    frame["question_chars"] = frame["question"].astype(str).str.len()
    frame["question_words"] = frame["question"].astype(str).str.split().str.len()
display(pd.concat({name: frame[["question_chars", "question_words"]].describe().T for name, frame in splits.items()}, names=["split", "measure"]))
duplicates = {name: int(frame["question"].str.casefold().str.strip().duplicated().sum()) for name, frame in splits.items()}
print("Normalized duplicate questions within split:", duplicates)
question_sets = {name: set(frame["question"].str.casefold().str.strip()) for name, frame in splits.items()}
print("Normalized cross-split overlaps:", {f"{a}/{b}": len(question_sets[a] & question_sets[b]) for a, b in [("train", "validation"), ("train", "synthetic_test"), ("validation", "synthetic_test")]})
family_counts = {name: int(frame["family_id"].nunique()) for name, frame in splits.items()}
family_sets = {name: set(frame["family_id"].dropna().astype(str)) for name, frame in splits.items()}
print("Template families by split:", family_counts)
print("Cross-split family overlap:", {f"{a}/{b}": len(family_sets[a] & family_sets[b]) for a, b in [("train", "validation"), ("train", "synthetic_test"), ("validation", "synthetic_test")]})
fig, axes = plt.subplots(1, 2, figsize=(13, 4))
pd.concat({name: frame["intent"].value_counts() for name, frame in splits.items()}, axis=1).fillna(0).plot.bar(ax=axes[0])
axes[0].set(title="Synthetic question counts by intent", ylabel="Rows", xlabel="Intent")
style_counts.plot.bar(ax=axes[1])
axes[1].set(title="Synthetic question counts by writing style", ylabel="Rows", xlabel="Style")
plt.tight_layout(); plt.show()
"""),
    markdown(5, """## Data preparation

The checked-in split files are already grouped by `family_id`: a template family stays in one split. This reduces leakage from near-identical generated phrasings across train, validation, and test. Fit TF-IDF only on training questions; the word n-grams capture terms and short phrases, while character n-grams help with spelling variation. The feature function below is imported directly from `train_assistant.py`, so it matches the command-line path exactly.
"""),
    code(6, """from train_assistant import (
    ABSTAIN, COMPARE_STORES_MIN_PRECISION, MIN_VALIDATION_COVERAGE, candidates,
    choose_intent_threshold, choose_threshold, cross_validate_candidates, evaluate,
    feature_union, heldout_by_source, probabilities, roc_auc_report,
)
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import Pipeline

x_train = train_df.question.astype(str).tolist()
y_train = train_df.intent.astype(str).tolist()
x_validation = validation_df.question.astype(str).tolist()
y_validation = validation_df.intent.astype(str).tolist()
vectorizer = feature_union()
X_train = vectorizer.fit_transform(x_train)
X_validation = vectorizer.transform(x_validation)
print("Training TF-IDF matrix:", X_train.shape, "| validation TF-IDF matrix:", X_validation.shape)
feature_names = vectorizer.get_feature_names_out()
examples = pd.DataFrame(X_train[:3].toarray(), columns=feature_names, index=train_df.question.head(3))
display(examples.loc[:, examples.sum(axis=0).sort_values(ascending=False).head(12).index])
diagnostic = LogisticRegression(C=3.0, max_iter=1500, random_state=42).fit(X_train, y_train)
top_features = []
for label_index, label in enumerate(diagnostic.classes_):
    top_indices = np.argsort(diagnostic.coef_[label_index])[-10:][::-1]
    top_features.extend({"intent": label, "feature": feature_names[index], "weight": diagnostic.coef_[label_index, index]} for index in top_indices)
display(pd.DataFrame(top_features))
"""),
    markdown(7, """## Modelling

All candidates use the exact `feature_union()` from the command-line script. Compare a majority-class baseline, Multinomial Naive Bayes, k-nearest neighbours, decision tree, balanced logistic regression, balanced calibrated linear SVM, random forest, and a small multilayer perceptron (MLP). Timing is measured at execution. The CLI candidates and global confidence threshold are selected by validation macro-F1 with abstentions; accepted accuracy and coverage break ties. Stratified, family-grouped five-fold CV on training data is reported separately as a robustness check and never changes model selection.
"""),
    code(8, """import time
from time import perf_counter
from sklearn.base import clone
from sklearn.dummy import DummyClassifier
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import accuracy_score, f1_score
from sklearn.neighbors import KNeighborsClassifier
from sklearn.neural_network import MLPClassifier
from sklearn.tree import DecisionTreeClassifier

TRAINING_STARTED = time.perf_counter()
model_candidates = {name: clone(model) for name, model in candidates().items()}
model_candidates.update({
    "KNeighbors": Pipeline([("features", feature_union()), ("classifier", KNeighborsClassifier(n_neighbors=5, metric="cosine", algorithm="brute"))]),
    "DecisionTree": Pipeline([("features", feature_union()), ("classifier", DecisionTreeClassifier(random_state=42))]),
    "RandomForest": Pipeline([("features", feature_union()), ("classifier", RandomForestClassifier(n_estimators=80, random_state=42, n_jobs=1))]),
    "MLP": Pipeline([("features", feature_union()), ("classifier", MLPClassifier(hidden_layer_sizes=(64,), max_iter=120, early_stopping=True, random_state=42))]),
})
fitted = {}
comparison = []
for name, model in model_candidates.items():
    started = perf_counter()
    model.fit(x_train, y_train)
    elapsed = perf_counter() - started
    prediction = model.predict(x_validation)
    classifier_params = model.named_steps["classifier"].get_params(deep=True)
    class_weight = classifier_params.get("class_weight")
    if class_weight is None:
        class_weight = classifier_params.get("estimator__class_weight", "not applicable")
    comparison.append({"model": name, "class_weight": class_weight, "validation_accuracy": accuracy_score(y_validation, prediction), "validation_macro_f1": f1_score(y_validation, prediction, average="macro", zero_division=0), "training_seconds": elapsed})
    fitted[name] = model
comparison_df = pd.DataFrame(comparison).sort_values(["validation_macro_f1", "validation_accuracy"], ascending=False).reset_index(drop=True)
display(comparison_df)
cv_metrics = cross_validate_candidates(
    x_train, y_train, train_df["family_id"].astype(str).tolist()
)
cv_df = pd.DataFrame([
    {"model": name, "macro_f1_mean": row["macro_f1_mean"],
     "macro_f1_std": row["macro_f1_std"], "fold_scores": row["fold_scores"]}
    for name, row in cv_metrics.items()
]).sort_values(["macro_f1_mean", "macro_f1_std"], ascending=[False, True])
display(cv_df)
"""),
    markdown(15, """### Training-cap sensitivity

The dataset builder supports the `ASSISTANT_CAP_MULTIPLIER` environment variable. This isolated comparison rebuilds temporary copies at 1.25 and 1.5, then chooses the best candidate within each cap by validation macro-F1 only. It does not replace the checked-in dataset used by the main notebook evaluation.
"""),
    code(16, """import shutil
import tempfile

import build_assistant_dataset as dataset_builder

def best_validation_score_for_cap(multiplier):
    with tempfile.TemporaryDirectory(prefix="assistant-cap-") as temporary:
        temporary_dir = Path(temporary)
        for filename in ["assistant_question_templates.csv", "assistant_slot_values.csv", "train_only_families.txt", "heldout_test_questions.csv", "human_test_questions.csv"]:
            source = DATA_DIR / filename
            if source.is_file():
                shutil.copy2(source, temporary_dir / filename)
        original = {name: getattr(dataset_builder, name) for name in ["ASSISTANT_DIR", "TEMPLATES_PATH", "SLOTS_PATH", "TRAIN_ONLY_FAMILIES_PATH", "OUTPUT_PATH", "SPLIT_DIR", "CAP_MULTIPLIER"]}
        try:
            dataset_builder.ASSISTANT_DIR = temporary_dir
            dataset_builder.TEMPLATES_PATH = temporary_dir / "assistant_question_templates.csv"
            dataset_builder.SLOTS_PATH = temporary_dir / "assistant_slot_values.csv"
            dataset_builder.TRAIN_ONLY_FAMILIES_PATH = temporary_dir / "train_only_families.txt"
            dataset_builder.OUTPUT_PATH = temporary_dir / "assistant_training_questions.csv"
            dataset_builder.SPLIT_DIR = temporary_dir / "splits"
            dataset_builder.CAP_MULTIPLIER = multiplier
            dataset_builder.main()
            capped_train = pd.read_csv(temporary_dir / "splits/train_questions.csv")
            capped_validation = pd.read_csv(temporary_dir / "splits/validation_questions.csv")
            x_fit = capped_train.question.astype(str).tolist()
            y_fit = capped_train.intent.astype(str).tolist()
            x_val = capped_validation.question.astype(str).tolist()
            y_val = capped_validation.intent.astype(str).tolist()
            scores = []
            for candidate_name, candidate in candidates().items():
                candidate.fit(x_fit, y_fit)
                score = f1_score(y_val, candidate.predict(x_val), average="macro", zero_division=0)
                scores.append((score, candidate_name))
            score, name = max(scores, key=lambda result: result[0])
            return {"cap_multiplier": multiplier, "selected_model": name, "validation_macro_f1": score}
        finally:
            for name, value in original.items():
                setattr(dataset_builder, name, value)

cap_comparison = pd.DataFrame([best_validation_score_for_cap(value) for value in (1.25, 1.5)])
display(cap_comparison)
"""),
    markdown(9, """## Evaluation

First inspect overfitting by comparing training and validation accuracy while varying tree depth, k, and logistic-regression C. Then choose the model, global confidence threshold, and a precision-targeted `compare_stores` cutoff using only validation labels. The synthetic test split and each held-out provenance group are evaluated separately and only once for final reporting. One-vs-rest ROC-AUC and ROC curves are additional threshold-independent ranking diagnostics on the synthetic test and AI-written held-out sets.

**Interpretation (Week 9):** accuracy can hide poor minority-intent performance when class frequencies differ. ROC-AUC measures ranking over thresholds, not calibrated probabilities or the precision/recall at the deployed cutoff; in imbalanced data it can look reassuring while positive-class precision is poor. Review per-intent metrics, confusion matrices, coverage, and real human questions too.
"""),
    code(10, """from sklearn.metrics import confusion_matrix, precision_recall_fscore_support, roc_curve

overfit_rows = []
for depth in [1, 2, 4, 8, None]:
    model = Pipeline([("features", feature_union()), ("classifier", DecisionTreeClassifier(max_depth=depth, random_state=42))]).fit(x_train, y_train)
    overfit_rows.append({"family": "tree depth", "setting": str(depth), "train_accuracy": accuracy_score(y_train, model.predict(x_train)), "validation_accuracy": accuracy_score(y_validation, model.predict(x_validation))})
for k in [1, 3, 5, 9, 15]:
    model = Pipeline([("features", feature_union()), ("classifier", KNeighborsClassifier(n_neighbors=k, metric="cosine", algorithm="brute"))]).fit(x_train, y_train)
    overfit_rows.append({"family": "kNN k", "setting": str(k), "train_accuracy": accuracy_score(y_train, model.predict(x_train)), "validation_accuracy": accuracy_score(y_validation, model.predict(x_validation))})
for c_value in [0.05, 0.2, 1.0, 3.0, 10.0]:
    model = Pipeline([("features", feature_union()), ("classifier", LogisticRegression(C=c_value, max_iter=1500, random_state=42))]).fit(x_train, y_train)
    overfit_rows.append({"family": "logistic C", "setting": str(c_value), "train_accuracy": accuracy_score(y_train, model.predict(x_train)), "validation_accuracy": accuracy_score(y_validation, model.predict(x_validation))})
overfit_df = pd.DataFrame(overfit_rows)
fig, axes = plt.subplots(1, 3, figsize=(14, 4))
for axis, family in zip(axes, ["tree depth", "kNN k", "logistic C"]):
    part = overfit_df[overfit_df.family.eq(family)]
    axis.plot(part.setting, part.train_accuracy, marker="o", label="train")
    axis.plot(part.setting, part.validation_accuracy, marker="o", label="validation")
    axis.set(title=family, xlabel="setting", ylabel="accuracy", ylim=(0, 1)); axis.legend()
plt.tight_layout(); plt.show()

validation_scores = {}
cli_candidate_names = candidates().keys()
for name in cli_candidate_names:
    model = fitted[name]
    classes, probs = probabilities(model, x_validation)
    threshold, threshold_metrics = choose_threshold(y_validation, classes, probs)
    validation_scores[name] = {"model": model, "threshold": threshold, "metrics": threshold_metrics, "validation_macro_f1": threshold_metrics["macro_f1_with_abstentions"]}
chosen_name = max(validation_scores, key=lambda name: (validation_scores[name]["validation_macro_f1"], validation_scores[name]["metrics"]["accepted_accuracy"], validation_scores[name]["metrics"]["coverage"]))
chosen_model = validation_scores[chosen_name]["model"]
threshold = validation_scores[chosen_name]["threshold"]
chosen_classes, chosen_probabilities = probabilities(chosen_model, x_validation)
compare_threshold, compare_threshold_metrics = choose_intent_threshold(
    y_validation, chosen_classes, chosen_probabilities, threshold,
    "compare_stores", COMPARE_STORES_MIN_PRECISION,
)
intent_thresholds = {"compare_stores": compare_threshold} if compare_threshold > threshold else {}
intent_threshold_selection = {
    "intent": "compare_stores",
    "minimum_precision": COMPARE_STORES_MIN_PRECISION,
    "validation_metrics": compare_threshold_metrics,
}
display(pd.DataFrame([{"model": name, "validation_macro_f1": row["validation_macro_f1"], "threshold": row["threshold"], **row["metrics"]} for name, row in validation_scores.items()]).sort_values(["validation_macro_f1", "accepted_accuracy", "coverage"], ascending=False))
print("Selected by validation macro-F1:", chosen_name, "| confidence threshold selected by accepted accuracy and coverage:", threshold)
print("Validation-selected compare_stores threshold:", compare_threshold, "| precision:", compare_threshold_metrics["precision"], "| recall:", compare_threshold_metrics["recall"])

val_classes, val_probs = probabilities(chosen_model, x_validation)
confidence = val_probs.max(axis=1)
threshold_grid = np.unique(np.r_[0.0, confidence])
coverage_accuracy = []
for cutoff in threshold_grid:
    accepted = confidence >= cutoff
    pred = val_classes[val_probs.argmax(axis=1)][accepted]
    coverage_accuracy.append({"threshold": cutoff, "coverage": float(accepted.mean()), "accepted_accuracy": float((pred == np.asarray(y_validation)[accepted]).mean()) if accepted.any() else np.nan})
coverage_df = pd.DataFrame(coverage_accuracy)
fig, axis = plt.subplots(figsize=(7, 4))
axis.plot(coverage_df.coverage, coverage_df.accepted_accuracy, marker=".")
axis.axvline(MIN_VALIDATION_COVERAGE, linestyle="--", label="minimum allowed validation coverage")
axis.set(title="Validation coverage versus accepted accuracy", xlabel="Coverage", ylabel="Accuracy on accepted questions", ylim=(0, 1)); axis.legend(); plt.tight_layout(); plt.show()

def report_metrics(name, rows, cutoff):
    with contextlib.redirect_stdout(io.StringIO()):
        return evaluate(name, chosen_model, rows, cutoff, intent_thresholds)

synthetic_test_rows = test_df.drop(columns=["question_chars", "question_words"], errors="ignore").astype(str).to_dict("records")
synthetic_metrics = report_metrics("Synthetic test split", synthetic_test_rows, threshold)
def show_evaluation(name, metrics):
    print(name, "rows:", metrics["rows"], "accuracy:", metrics["accuracy"], "macro-F1:", metrics["macro_f1"], "coverage:", metrics["coverage"])
    labels = metrics["confusion_labels"]
    display(pd.DataFrame(metrics["per_intent"]).T)
    fig, axis = plt.subplots(figsize=(8, 6))
    matrix = np.asarray(metrics["confusion_matrix"])
    image = axis.imshow(matrix, cmap="Blues"); axis.set_xticks(range(len(labels)), labels, rotation=60, ha="right"); axis.set_yticks(range(len(labels)), labels)
    axis.set(xlabel="Predicted", ylabel="Actual", title=name + " confusion matrix"); fig.colorbar(image, ax=axis); plt.tight_layout(); plt.show()
show_evaluation("Synthetic test split (synthetic generated questions)", synthetic_metrics)

heldout_path = DATA_DIR / "heldout_test_questions.csv"
heldout_df = pd.read_csv(heldout_path, dtype=str).fillna("")
heldout_groups = heldout_by_source(heldout_df.to_dict("records"))
heldout_metrics = {}
for source, group in heldout_groups.items():
    rows = [{**row, "intent": row["expected_intent"]} for row in group]
    metrics = report_metrics(f"Held-out ({source})", rows, threshold)
    heldout_metrics[source] = metrics
    show_evaluation(f"Held-out {source} provenance", metrics)
human_path = DATA_DIR / "human_test_questions.csv"
human_metrics = None
if human_path.is_file():
    human_df = pd.read_csv(human_path, dtype=str).fillna("")
    label_col = "expected_intent" if "expected_intent" in human_df else "intent"
    human_rows = [{**row, "expected_intent": row[label_col], "intent": row[label_col], "source": "human_written"} for row in human_df.to_dict("records")]
    human_metrics = report_metrics("Human-written held-out set", human_rows, threshold)
    show_evaluation("Human-written held-out provenance", human_metrics)
else:
    print("Human-written held-out set: not present; no human metrics reported.")

roc_metrics = {
    "synthetic_test": roc_auc_report(chosen_model, synthetic_test_rows),
    "ai_written_heldout": roc_auc_report(chosen_model, heldout_groups.get("ai_written", [])),
}
def plot_roc_curves(title, rows):
    if not rows:
        print(title, "ROC curves unavailable: no rows.")
        return
    questions = [row["question"] for row in rows]
    truth = np.asarray([row.get("intent") or row["expected_intent"] for row in rows])
    classes, probability_values = probabilities(chosen_model, questions)
    fig, axis = plt.subplots(figsize=(8, 6))
    for index, intent in enumerate(classes.astype(str)):
        binary_truth = truth == intent
        if binary_truth.any() and (~binary_truth).any():
            fpr, tpr, _ = roc_curve(binary_truth, probability_values[:, index])
            auc = roc_metrics["synthetic_test" if "synthetic" in title.lower()
                              else "ai_written_heldout"]["per_intent_auc_ovr"][intent]
            axis.plot(fpr, tpr, label=f"{intent} (AUC={auc:.3f})")
    axis.plot([0, 1], [0, 1], linestyle="--", color="black", label="chance")
    axis.set(title=title, xlabel="False positive rate", ylabel="True positive rate")
    axis.legend(loc="lower right", fontsize="small")
    plt.tight_layout(); plt.show()

display(pd.DataFrame(roc_metrics).T)
plot_roc_curves("One-vs-rest ROC — synthetic test", synthetic_test_rows)
plot_roc_curves(
    "One-vs-rest ROC — AI-written held-out",
    heldout_groups.get("ai_written", []),
)
"""),
    markdown(11, """## Deployment

Save the selected pipeline and `metadata.json` using the exact keys and value shapes written by `scripts/train_assistant.py`. Then load through `price_check_api.assistant_model` and answer examples through `price_check_api.trained_assistant.answer_trained_question`. Deterministic answers still depend on source data availability; model confidence is not a correctness guarantee.

**Limitations:** the training questions are synthetic variants of AI-written templates; the separate held-out set is AI-written, not human validation. Rare wording, Swahili/sheng, new entities, and drift may cause errors. Abstention helps but does not eliminate misrouting. This intent model is not a price predictor and must not create supermarket prices or forecasts.
"""),
    code(12, """import hashlib
import json
from datetime import date
import joblib
import sklearn

train_file = SPLIT_DIR / "train_questions.csv"
metadata = {
    "model_name": chosen_name,
    "training_date": date.today().isoformat(),
    "sklearn_version": sklearn.__version__,
    "training_data_sha256": hashlib.sha256(train_file.read_bytes()).hexdigest(),
    "training_wall_seconds": time.perf_counter() - TRAINING_STARTED,
    "training_rows": len(train_df),
    "validation_rows": len(validation_df),
    "synthetic_test_rows": len(test_df),
    "heldout_rows_by_source": {source: len(rows) for source, rows in heldout_by_source(heldout_df.to_dict("records")).items()},
    "confidence_threshold": threshold,
    "intent_confidence_thresholds": intent_thresholds,
    "intent_threshold_selection": intent_threshold_selection,
    "minimum_validation_coverage": MIN_VALIDATION_COVERAGE,
    "leakage": json.loads((DATA_DIR / "dataset_build_metadata.json").read_text(encoding="utf-8")) if (DATA_DIR / "dataset_build_metadata.json").is_file() else {},
    "metrics": {
        "validation": validation_scores[chosen_name]["metrics"],
        "synthetic_test": synthetic_metrics,
        "synthetic_test_dummy_baseline": None,
        "heldout_by_source": heldout_metrics,
        "heldout_dummy_by_source": {},
    },
    "cross_validation": cv_metrics,
    "roc_auc": roc_metrics,
}
dummy_model = candidates()["DummyMostFrequent"].fit(x_train, y_train)
with contextlib.redirect_stdout(io.StringIO()):
    metadata["metrics"]["synthetic_test_dummy_baseline"] = evaluate("Synthetic test majority baseline", dummy_model, synthetic_test_rows, None)
    metadata["metrics"]["heldout_dummy_by_source"] = {
        source: evaluate(f"Held-out {source} majority baseline", dummy_model,
                         [{**row, "intent": row["expected_intent"]} for row in group], None)
        for source, group in heldout_by_source(heldout_df.to_dict("records")).items()
    }
if human_metrics is not None:
    metadata["heldout_rows_by_source"]["human_written"] = len(human_df)
    metadata["metrics"]["heldout_by_source"]["human_written"] = human_metrics
    human_rows_for_baseline = [{**row, "expected_intent": row["intent"]} for row in human_rows]
    with contextlib.redirect_stdout(io.StringIO()):
        metadata["metrics"]["heldout_dummy_by_source"]["human_written"] = evaluate(
            "Human-written held-out majority baseline", dummy_model, human_rows_for_baseline, None
        )
MODEL_DIR.mkdir(parents=True, exist_ok=True)
joblib.dump(chosen_model, MODEL_DIR / "intent_pipeline.joblib")
(MODEL_DIR / "metadata.json").write_text(json.dumps(metadata, indent=2), encoding="utf-8")
print("Saved model artifact and metadata in configured model directory.")

import price_check_api.assistant_model as assistant_model_module
assistant_model_module.MODEL_DIR = MODEL_DIR
from price_check_api.assistant_model import load_assistant_model
from price_check_api.trained_assistant import answer_trained_question
import price_check_api.trained_assistant as trained_assistant_module
trained_assistant_module.load_assistant_model = lambda: load_assistant_model(MODEL_DIR)
loaded = load_assistant_model()
print("Loader available:", loaded.pipeline is not None)
sample_questions = ["Where can I find the cheapest milk?", "What is the price of maize in Nairobi?", "Compare maize prices between markets", "How has food inflation changed?", "Tell me the weather tomorrow"]
for question in sample_questions:
    answer = answer_trained_question(question)
    print("Q:", question, "\\nA:", answer.answer, "\\nsource:", answer.source_name, answer.source_url, "\\ncoverage:", answer.coverage_start, answer.coverage_end)
"""),
    markdown(13, """### Training-path consistency check

The notebook pipeline is compared with `python scripts/train_assistant.py` on the same local data. The command-line script writes to its default backend/models path, so existing artifacts there are backed up and restored after comparison. Model selection, threshold, and synthetic test metrics are compared directly; a difference is reported without concealment.
"""),
    code(14, """import subprocess
import sys
from pathlib import Path

default_model_dir = ROOT / "backend/models"
artifact_names = ["intent_pipeline.joblib", "metadata.json"]
backup = {name: (default_model_dir / name).read_bytes() if (default_model_dir / name).is_file() else None for name in artifact_names}
try:
    run = subprocess.run([sys.executable, str(ROOT / "backend/scripts/train_assistant.py")], cwd=ROOT / "backend", capture_output=True, text=True, check=False)
    if run.returncode:
        print("CLI consistency check could not complete; exit:", run.returncode)
        print(run.stderr[-4000:])
    else:
        cli_metadata = json.loads((default_model_dir / "metadata.json").read_text(encoding="utf-8"))
        differences = {
            "model_name": metadata["model_name"] != cli_metadata["model_name"],
            "confidence_threshold": metadata["confidence_threshold"] != cli_metadata["confidence_threshold"],
            "intent_confidence_thresholds": metadata["intent_confidence_thresholds"] != cli_metadata["intent_confidence_thresholds"],
            "synthetic_test_accuracy": metadata["metrics"]["synthetic_test"]["accuracy"] != cli_metadata["metrics"]["synthetic_test"]["accuracy"],
            "synthetic_test_macro_f1": metadata["metrics"]["synthetic_test"]["macro_f1"] != cli_metadata["metrics"]["synthetic_test"]["macro_f1"],
        }
        display(pd.DataFrame([{"field": key, "notebook": metadata["model_name"] if key == "model_name" else metadata["confidence_threshold"] if key == "confidence_threshold" else metadata["intent_confidence_thresholds"] if key == "intent_confidence_thresholds" else metadata["metrics"]["synthetic_test"]["accuracy"] if key.endswith("accuracy") else metadata["metrics"]["synthetic_test"]["macro_f1"], "command_line": cli_metadata["model_name"] if key == "model_name" else cli_metadata["confidence_threshold"] if key == "confidence_threshold" else cli_metadata["intent_confidence_thresholds"] if key == "intent_confidence_thresholds" else cli_metadata["metrics"]["synthetic_test"]["accuracy"] if key.endswith("accuracy") else cli_metadata["metrics"]["synthetic_test"]["macro_f1"], "different": value} for key, value in differences.items()]))
        print("Consistency check:", "MATCH" if not any(differences.values()) else "DIFFERENCE FOUND")
finally:
    default_model_dir.mkdir(parents=True, exist_ok=True)
    for name, contents in backup.items():
        path = default_model_dir / name
        if contents is None:
            path.unlink(missing_ok=True)
        else:
            path.write_bytes(contents)
    # Leave the notebook's selected artifact in place when its configured output is the default.
    if MODEL_DIR.resolve() == default_model_dir.resolve():
        joblib.dump(chosen_model, MODEL_DIR / "intent_pipeline.joblib")
        (MODEL_DIR / "metadata.json").write_text(json.dumps(metadata, indent=2), encoding="utf-8")
"""),
]


def _sanitize(text: str) -> str:
    roots = [str(ROOT), str(ROOT).replace("\\", "/")]
    for value in roots:
        text = text.replace(value, "<REPOSITORY>")
    text = re.sub(r"[A-Za-z]:\\Users\\[^\\\s]+", "<USER_HOME>", text)
    text = re.sub(r"/home/[^/\s]+", "<USER_HOME>", text)
    text = re.sub(r"/mnt/[a-z]/Users/[^/\s]+", "<USER_HOME>", text)
    return text


def execute(notebook: dict[str, Any]) -> None:
    """Execute cells in a shared namespace and persist text/image outputs without a kernel install."""
    os.environ.setdefault("MPLBACKEND", "Agg")
    namespace: dict[str, Any] = {"__name__": "__main__"}
    try:
        import matplotlib

        matplotlib.use("Agg")
    except ImportError as error:
        raise RuntimeError("matplotlib is required to execute this notebook; install it in the existing environment.") from error

    for index, cell in enumerate(notebook["cells"]):
        if cell["cell_type"] != "code":
            continue
        source = "".join(cell["source"])
        stream = io.StringIO()
        outputs: list[dict[str, Any]] = []
        cell["execution_count"] = index
        try:
            with contextlib.redirect_stdout(stream), contextlib.redirect_stderr(stream):
                exec(compile(source, f"<notebook-cell-{index}>", "exec"), namespace)
        except Exception:
            outputs.append({"output_type": "error", "ename": "NotebookCellError", "evalue": _sanitize(traceback.format_exc().splitlines()[-1]), "traceback": [_sanitize(line) for line in traceback.format_exc().splitlines()]})
            cell["outputs"] = outputs
            raise RuntimeError(f"Notebook execution failed in code cell {index}: {_sanitize(traceback.format_exc())}") from None
        text = _sanitize(stream.getvalue())
        if text:
            outputs.append({"output_type": "stream", "name": "stdout", "text": text.splitlines(keepends=True)})
        try:
            import matplotlib.pyplot as plt

            for figure_number in plt.get_fignums():
                image_buffer = io.BytesIO()
                plt.figure(figure_number).savefig(image_buffer, format="png", bbox_inches="tight")
                outputs.append({"output_type": "display_data", "data": {"image/png": base64.b64encode(image_buffer.getvalue()).decode("ascii"), "text/plain": ["<Figure>"]}, "metadata": {}})
            plt.close("all")
        except ImportError:
            pass
        cell["outputs"] = outputs


def main() -> None:
    DESTINATION.parent.mkdir(parents=True, exist_ok=True)
    notebook = {
        "cells": CELLS,
        "metadata": {"kernelspec": {"display_name": "Python 3", "language": "python", "name": "python3"}, "language_info": {"name": "python", "version": "3"}},
        "nbformat": 4,
        "nbformat_minor": 5,
    }
    try:
        execute(notebook)
    except RuntimeError as error:
        # Preserve a runnable notebook skeleton and the actionable reason when
        # this machine lacks the already-required offline ML dependencies.
        notebook["cells"][0]["outputs"] = [{
            "output_type": "stream",
            "name": "stderr",
            "text": [_sanitize(str(error)) + "\n"],
        }]
        notebook["cells"][0]["execution_count"] = 0
        DESTINATION.write_text(json.dumps(notebook, indent=1), encoding="utf-8")
        raise
    DESTINATION.write_text(json.dumps(notebook, indent=1), encoding="utf-8")
    print("Executed and saved notebooks/assistant_intent_crisp_dm.ipynb")


if __name__ == "__main__":
    main()
