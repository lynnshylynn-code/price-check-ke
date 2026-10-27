"""Fit the listing-name index and select its fallback threshold on validation rows."""

from __future__ import annotations

import csv
import difflib
import hashlib
import json
import re
from datetime import date
from pathlib import Path

import joblib
import numpy as np
import sklearn
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

from price_check_api.listings import get_listings

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data/assistant"
MODEL_DIR = ROOT / "models"
MODEL_PATH = MODEL_DIR / "entity_linker.joblib"
METADATA_PATH = MODEL_DIR / "entity_linker_metadata.json"


def read_rows(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8", newline="") as source:
        return list(csv.DictReader(source))


def main() -> None:
    slots = read_rows(DATA / "assistant_slot_values.csv")
    surfaces = {row["surface_form"]: row["canonical"] for row in slots if row["slot"] == "product"}
    names = sorted({item.item_name for item in get_listings()} | set(surfaces))
    vectorizer = TfidfVectorizer(analyzer="char_wb", ngram_range=(3, 5), lowercase=True)
    matrix = vectorizer.fit_transform(names)
    validation = read_rows(DATA / "splits/validation_questions.csv")
    examples: list[tuple[str, str | None]] = []
    store_examples: list[tuple[float, str | None]] = []
    for row in validation:
        entities = json.loads(row["entities"])
        if entities.get("product"):
            examples.append((row["question"], str(entities["product"]).casefold()))
        elif entities.get("unknown_product"):
            examples.append((row["question"], None))
        if entities.get("store") or entities.get("other_store") is not None:
            expected_store = str(entities.get("store") or "").casefold() or None
            words = re.findall(r"[a-z0-9]+", row["question"].casefold())
            best = 0.0
            for slot in (item for item in slots if item["slot"] == "store"):
                target = slot["surface_form"].casefold()
                width = max(1, len(target.split()))
                for start in range(max(1, len(words) - width + 1)):
                    candidate = " ".join(words[start : start + width])
                    best = max(best, difflib.SequenceMatcher(None, candidate, target).ratio())
            store_examples.append((best, expected_store))

    thresholds = np.linspace(0.05, 0.95, 91)
    best_threshold, best_accuracy = 0.25, -1.0
    for threshold in thresholds:
        correct = 0
        for question, expected in examples:
            score = cosine_similarity(vectorizer.transform([question]), matrix)[0]
            index = int(score.argmax())
            confidence = float(score[index])
            alias_value = surfaces.get(names[index], names[index]).casefold()
            predicted = alias_value if confidence >= threshold else None
            correct += int(predicted == expected)
        accuracy = correct / max(1, len(examples))
        if accuracy > best_accuracy:
            best_accuracy, best_threshold = accuracy, float(threshold)

    best_store_accuracy = -1.0
    store_threshold = 0.75
    for threshold in sorted({score for score, _ in store_examples} | {0.0}):
        correct = sum(
            (score >= threshold) == (expected is not None) for score, expected in store_examples
        )
        accuracy = correct / max(1, len(store_examples))
        if accuracy >= best_store_accuracy:
            best_store_accuracy, store_threshold = accuracy, threshold
    artifact = {
        "vectorizer": vectorizer,
        "matrix": matrix,
        "names": names,
        "product_surface_to_canonical": surfaces,
        "product_similarity_threshold": best_threshold,
        "store_similarity_threshold": store_threshold,
    }
    MODEL_DIR.mkdir(parents=True, exist_ok=True)
    joblib.dump(artifact, MODEL_PATH)
    data_hash = hashlib.sha256(
        (DATA / "assistant_slot_values.csv").read_bytes()
        + (DATA / "splits/validation_questions.csv").read_bytes()
    ).hexdigest()
    metadata = {
        "model_name": "Character TF-IDF entity linker",
        "training_date": date.today().isoformat(),
        "sklearn_version": sklearn.__version__,
        "training_data_sha256": data_hash,
        "validation_rows": len(examples),
        "product_similarity_threshold": best_threshold,
        "validation_accuracy": best_accuracy,
        "store_similarity_threshold": store_threshold,
        "store_validation_accuracy": best_store_accuracy,
    }
    METADATA_PATH.write_text(json.dumps(metadata, indent=2), encoding="utf-8")
    print(json.dumps(metadata, indent=2))


if __name__ == "__main__":
    main()
