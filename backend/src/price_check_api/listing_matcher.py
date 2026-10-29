"""Runtime access to the optional trained listing matcher."""

from __future__ import annotations

import re
from difflib import SequenceMatcher
from functools import lru_cache
from pathlib import Path
from typing import Any

import joblib
from sklearn.feature_extraction.text import TfidfVectorizer

from .listings import get_uom_map, parse_pack_size

MODEL_DIR = Path(__file__).resolve().parents[2] / "models"


def pair_features(
    left: Any, right: Any, word: TfidfVectorizer, char: TfidfVectorizer
) -> list[float]:
    left_name, right_name = left.item_name, right.item_name
    left_tokens = set(re.findall(r"[a-z0-9]+", left_name.casefold()))
    right_tokens = set(re.findall(r"[a-z0-9]+", right_name.casefold()))
    token_ratio = 2 * len(left_tokens & right_tokens) / max(1, len(left_tokens) + len(right_tokens))
    word_cosine = float(
        (word.transform([left_name]) @ word.transform([right_name]).T).toarray()[0, 0]
    )
    char_cosine = float(
        (char.transform([left_name]) @ char.transform([right_name]).T).toarray()[0, 0]
    )
    left_size = parse_pack_size(left.pack_size, get_uom_map())
    right_size = parse_pack_size(right.pack_size, get_uom_map())
    left_brand = re.search(r"[a-z0-9]+", left_name.casefold())
    right_brand = re.search(r"[a-z0-9]+", right_name.casefold())
    left_brand = left_brand.group(0) if left_brand else ""
    right_brand = right_brand.group(0) if right_brand else ""
    left_unit_price = left.unit_price or 0.0
    right_unit_price = right.unit_price or 0.0
    ratio = (
        min(left_unit_price, right_unit_price) / max(left_unit_price, right_unit_price)
        if left_unit_price and right_unit_price
        else 0.0
    )
    return [
        token_ratio,
        word_cosine,
        char_cosine,
        float(left_size is not None and left_size == right_size),
        float(left.unit == right.unit and left.unit is not None),
        float(left_brand == right_brand and left_brand != ""),
        abs(len(left_name) - len(right_name)) / max(1, max(len(left_name), len(right_name))),
        ratio,
        SequenceMatcher(None, left_name.casefold(), right_name.casefold()).ratio(),
    ]


@lru_cache(maxsize=1)
def load_matcher() -> dict[str, Any] | None:
    path = MODEL_DIR / "listing_matcher.joblib"
    if not path.is_file():
        return None
    try:
        return joblib.load(path)
    except (OSError, ValueError, TypeError):
        return None


def predict_match(left: Any, right: Any) -> bool | None:
    artifact = load_matcher()
    if artifact is None:
        return None
    word: TfidfVectorizer = artifact["word_vectorizer"]
    char: TfidfVectorizer = artifact["char_vectorizer"]
    features = pair_features(left, right, word, char)
    model = artifact["classifier"]
    return bool(model.predict([features])[0])
