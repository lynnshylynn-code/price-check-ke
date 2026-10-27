"""Train a listing pair classifier from human labels or synthetic bootstrap pairs."""

from __future__ import annotations

import csv
import hashlib
import json
import random
from datetime import date
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import joblib
import numpy as np
import sklearn
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import confusion_matrix, precision_recall_fscore_support
from sklearn.model_selection import GroupShuffleSplit

from price_check_api.listing_groups import _match_score
from price_check_api.listing_matcher import pair_features
from price_check_api.listings import Listing, get_listings, get_uom_map, parse_pack_size

ROOT = Path(__file__).resolve().parents[1]
LABELS = ROOT / "data/labels/match_pairs.csv"
MODEL_DIR = ROOT / "models"
MODEL_PATH = MODEL_DIR / "listing_matcher.joblib"
METADATA_PATH = MODEL_DIR / "listing_matcher_metadata.json"
SEED = 42


def _synthetic_pairs() -> list[tuple[Any, Any, int, str]]:
    listings = get_listings()
    pairs: list[tuple[Any, Any, int, str]] = []
    by_brand: dict[str, list[Listing]] = {}
    for item in listings:
        brand = item.item_name.split()[0].casefold() if item.item_name.split() else ""
        by_brand.setdefault(brand, []).append(item)
        noisy = SimpleNamespace(
            item_name=item.item_name.lower().replace(" ", "  ", 1),
            pack_size=item.pack_size,
            unit=item.unit,
            unit_price=item.unit_price,
        )
        pairs.append((item, noisy, 1, item.id))
    for _brand, items in by_brand.items():
        for index, left in enumerate(items):
            left_size = parse_pack_size(left.pack_size, get_uom_map())
            for right in items[index + 1 :]:
                right_size = parse_pack_size(right.pack_size, get_uom_map())
                if left_size is not None and right_size is not None and left_size != right_size:
                    pairs.append((left, right, 0, left.id))
                    break
    return pairs


def _human_pairs() -> list[tuple[Listing, Listing, int, str]]:
    by_id = {item.id: item for item in get_listings()}
    result = []
    with LABELS.open(encoding="utf-8", newline="") as source:
        for row in csv.DictReader(source):
            label = row.get("label", "").strip()
            if label not in {"0", "1"}:
                continue
            left, right = by_id.get(row["id_a"]), by_id.get(row["id_b"])
            if left and right:
                result.append((left, right, int(label), left.id))
    return result


def _metrics(y_true: list[int], y_pred: list[int]) -> dict[str, Any]:
    precision, recall, f1, support = precision_recall_fscore_support(
        y_true,
        y_pred,
        labels=[0, 1],
        zero_division=0,
    )
    return {
        "precision": float(precision[1]),
        "recall": float(recall[1]),
        "f1": float(f1[1]),
        "confusion_matrix_labels": [0, 1],
        "confusion_matrix": confusion_matrix(y_true, y_pred, labels=[0, 1]).tolist(),
        "sample_size": len(y_true),
        "positive_count": int(support[1]),
    }


def main() -> None:
    random.seed(SEED)
    human = _human_pairs()
    pairs = (
        human if len(human) >= 20 and len({item[2] for item in human}) == 2 else _synthetic_pairs()
    )
    source = "human-labelled" if pairs is human else "synthetic bootstrap"
    texts = [name for left, right, _, _ in pairs for name in (left.item_name, right.item_name)]
    word = TfidfVectorizer(ngram_range=(1, 2), lowercase=True).fit(texts)
    char = TfidfVectorizer(analyzer="char_wb", ngram_range=(2, 5), lowercase=True).fit(texts)
    X = np.asarray([pair_features(left, right, word, char) for left, right, _, _ in pairs])
    y = np.asarray([label for _, _, label, _ in pairs])
    groups = np.asarray([group for *_, group in pairs])
    split = GroupShuffleSplit(n_splits=1, test_size=0.25, random_state=SEED)
    train_idx, test_idx = next(split.split(X, y, groups))
    classifier = LogisticRegression(class_weight="balanced", max_iter=1000, random_state=SEED)
    classifier.fit(X[train_idx], y[train_idx])
    predicted = classifier.predict(X[test_idx]).astype(int).tolist()
    baseline = [
        int(_match_score(pairs[index][0].item_name, pairs[index][1].item_name) >= 0.70)
        for index in test_idx
    ]
    model_metrics = _metrics(y[test_idx].astype(int).tolist(), predicted)
    baseline_metrics = _metrics(y[test_idx].astype(int).tolist(), baseline)
    data_bytes = LABELS.read_bytes() if source == "human-labelled" else "\n".join(texts).encode()
    metadata = {
        "model_name": "LogisticRegression listing pair matcher",
        "training_date": date.today().isoformat(),
        "sklearn_version": sklearn.__version__,
        "training_data_sha256": hashlib.sha256(data_bytes).hexdigest(),
        "source": source,
        "training_sample_size": len(train_idx),
        "evaluation_sample_size": len(test_idx),
        "positives": int(y.sum()),
        "metrics": {"matcher": model_metrics, "old_threshold_baseline": baseline_metrics},
    }
    MODEL_DIR.mkdir(parents=True, exist_ok=True)
    joblib.dump(
        {"classifier": classifier, "word_vectorizer": word, "char_vectorizer": char}, MODEL_PATH
    )
    METADATA_PATH.write_text(json.dumps(metadata, indent=2), encoding="utf-8")
    print(json.dumps(metadata, indent=2))


if __name__ == "__main__":
    main()
