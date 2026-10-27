"""Deterministic answers routed by the locally trained intent model."""

from __future__ import annotations

import csv
import re
from difflib import SequenceMatcher
from functools import lru_cache
from pathlib import Path
from typing import Any

from .assistant_model import load_assistant_model
from .listing_groups import get_comparable_groups
from .listings import DATA_LABEL, get_listings, search_listings
from .market_data import (
    SOURCE_NAME,
    SOURCE_URL,
    get_food_inflation_response,
    get_market_directory,
    get_market_prices,
)
from .schemas import MarketQuestionResponse

ASSISTANT_DATA = Path(__file__).resolve().parents[2] / "data/assistant"
EXAMPLES = "Try asking: ‘cheapest sugar 2kg?’, ‘beans price in Kitui’, or ‘food inflation latest’."
MODEL_VERSION = "synthetic-intent-v1"


@lru_cache(maxsize=1)
def _slot_values() -> dict[str, list[dict[str, str]]]:
    result: dict[str, list[dict[str, str]]] = {}
    with (ASSISTANT_DATA / "assistant_slot_values.csv").open(
        encoding="utf-8", newline=""
    ) as source:
        for row in csv.DictReader(source):
            result.setdefault(row["slot"], []).append(row)
    return result


def _extract(question: str, slot: str) -> dict[str, str] | None:
    values = sorted(
        _slot_values().get(slot, []), key=lambda row: len(row["surface_form"]), reverse=True
    )
    normalized = question.casefold()
    for row in values:
        surface = row["surface_form"]
        if surface and re.search(rf"(?<!\w){re.escape(surface.casefold())}(?!\w)", normalized):
            return row
    return None


def _resolve_product(question: str) -> tuple[str | None, str | None, float]:
    row = _extract(question, "product") or _extract(question, "unknown_product")
    if row:
        return row["canonical"], row["surface_form"], 1.0
    candidates = _product_candidates()
    vectorizer, matrix, names, threshold, aliases = candidates
    from sklearn.metrics.pairwise import cosine_similarity

    scores = cosine_similarity(vectorizer.transform([question]), matrix)[0]
    index = int(scores.argmax())
    score = float(scores[index])
    match = names[index]
    value = aliases.get(match, match).casefold()
    return (value, match, score) if score >= threshold else (None, None, score)


def _resolve_store(question: str) -> tuple[str | None, float, bool]:
    unknown = _extract(question, "other_store")
    if unknown:
        return None, 1.0, True
    exact = _extract(question, "store")
    if exact:
        return exact["canonical"], 1.0, False
    words = re.findall(r"[a-z0-9]+", question.casefold())
    best_row: dict[str, str] | None = None
    best_score = 0.0
    for row in _slot_values().get("store", []):
        target = row["surface_form"].casefold()
        width = max(1, len(target.split()))
        for start in range(max(1, len(words) - width + 1)):
            candidate = " ".join(words[start : start + width])
            score = SequenceMatcher(None, candidate, target).ratio()
            if score > best_score:
                best_row, best_score = row, score
    threshold = _linker_metadata().get("store_similarity_threshold", 0.75)
    return (
        (best_row["canonical"], best_score, False)
        if best_row and best_score >= float(threshold)
        else (None, best_score, False)
    )


def _resolve_county(question: str) -> tuple[str | None, bool]:
    slot = _extract(question, "county")
    if slot:
        return slot["canonical"], False
    counties, markets = get_market_directory()
    candidates = sorted(
        {(county, county) for county in counties}
        | {(market.name, market.county) for market in markets},
        key=lambda item: len(item[0]),
        reverse=True,
    )
    for name, county in candidates:
        if re.search(rf"(?<!\w){re.escape(name.casefold())}(?!\w)", question.casefold()):
            return county, False
    location = re.search(r"\b(?:in|at|for)\s+([a-z][a-z -]{1,40})", question.casefold())
    return ("not in the snapshot", True) if location else (None, False)


@lru_cache(maxsize=1)
def _linker_metadata() -> dict[str, Any]:
    path = Path(__file__).resolve().parents[2] / "models/entity_linker_metadata.json"
    try:
        import json

        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}


@lru_cache(maxsize=1)
def _product_candidates() -> tuple[Any, Any, list[str], float, dict[str, str]]:
    artifact_path = Path(__file__).resolve().parents[2] / "models/entity_linker.joblib"
    if artifact_path.is_file():
        try:
            import joblib

            artifact = joblib.load(artifact_path)
            return (
                artifact["vectorizer"],
                artifact["matrix"],
                artifact["names"],
                float(artifact["product_similarity_threshold"]),
                artifact["product_surface_to_canonical"],
            )
        except (OSError, ValueError, KeyError, TypeError):
            pass
    from sklearn.feature_extraction.text import TfidfVectorizer

    names = sorted(
        {item.item_name for item in get_listings()}
        | {row["surface_form"] for row in _slot_values().get("product", [])}
    )
    vectorizer = TfidfVectorizer(analyzer="char_wb", ngram_range=(3, 5), lowercase=True)
    matrix = vectorizer.fit_transform(names)
    return vectorizer, matrix, names, 0.25, {}


def _classify(question: str) -> tuple[str, float, str | None]:
    state = load_assistant_model()
    if state.pipeline is None:
        return "out_of_scope", 0.0, state.error
    probabilities = state.pipeline.predict_proba([question])[0]
    index = int(probabilities.argmax())
    confidence = float(probabilities[index])
    intent = str(state.pipeline.classes_[index])
    if confidence < float(state.metadata.get("confidence_threshold", 1.0)):
        return "out_of_scope", confidence, None
    return intent, confidence, None


def _base_response(
    question: str,
    intent: str,
    confidence: float,
    entities: dict[str, Any],
    answer: str,
    sources: list[dict[str, str]],
    source_name: str | None = None,
    source_url: str | None = None,
    coverage_start: str | None = None,
    coverage_end: str | None = None,
) -> MarketQuestionResponse:
    return MarketQuestionResponse(
        answer=answer,
        source_name=source_name or "Price Check KE data snapshots",
        source_url=source_url,
        coverage_start=coverage_start,
        coverage_end=coverage_end,
        sources=sources,
        intent=intent,
        intent_confidence=confidence,
        entities=entities,
        model_version=MODEL_VERSION,
    )


def answer_trained_question(question: str) -> MarketQuestionResponse:
    text = question.strip()
    intent, confidence, load_error = _classify(text)
    if load_error:
        return _base_response(
            text,
            intent,
            confidence,
            {},
            f"I can't answer that from the data I have. {load_error} {EXAMPLES}",
            [],
        )
    if re.search(
        r"\b(forecast|predict|next month|future|buying advice|should i buy|in stock|"
        r"stock|delivery)\b",
        text.casefold(),
    ):
        return _base_response(
            text,
            "out_of_scope",
            confidence,
            {},
            "This dataset does not support forecasts, stock or delivery claims, or buying advice. "
            + EXAMPLES,
            [],
        )
    if re.search(
        r"\b(ignore (all )?(the )?rules|reveal secrets|system prompt|developer instructions)\b",
        text.casefold(),
    ):
        return _base_response(
            text,
            "out_of_scope",
            confidence,
            {},
            f"I can't answer that from the data I have. {EXAMPLES}",
            [],
        )
    if intent == "out_of_scope":
        return _base_response(
            text,
            intent,
            confidence,
            {},
            f"I can't answer that from the data I have. {EXAMPLES}",
            [],
        )

    store, store_similarity, unknown_store = _resolve_store(text)
    product, product_label, product_score = _resolve_product(text)
    unknown_product = _extract(text, "unknown_product")
    if unknown_product:
        product = None
        product_label = unknown_product["surface_form"]
    entities: dict[str, Any] = {
        "product": product,
        "product_label": product_label,
        "product_similarity": round(product_score, 4),
    }
    if store is not None or unknown_store:
        entities["store"] = store or "not in the snapshot"
        entities["store_similarity"] = round(store_similarity, 4)

    if intent in {
        "cheapest_item",
        "price_at_store",
        "biggest_discount",
        "unit_price",
        "compare_stores",
    }:
        group_row = _extract(text, "group")
        if group_row:
            entities["group"] = group_row["canonical"] or None
        elif product:
            entities["group"] = None
        if entities.get("store") == "not in the snapshot" or product is None:
            return _base_response(
                text,
                intent,
                confidence,
                entities,
                f"That product or store is not in the snapshot. {DATA_LABEL}.",
                [],
            )
        query = str(entities.get("group") or product_label or "")
        if intent == "biggest_discount":
            rows = sorted(
                (item for item in get_listings() if item.discount_pct is not None),
                key=lambda item: item.discount_pct or 0,
                reverse=True,
            )[:5]
        elif intent == "compare_stores" and entities.get("group"):
            group = next(
                (group for group in get_comparable_groups() if group.id == entities["group"]), None
            )
            rows = list(group.listings) if group else []
        else:
            rows = list(
                search_listings(
                    query, str(entities["store"]) if entities.get("store") else None, False, None, 8
                )
            )
        if intent == "unit_price":
            rows = sorted(
                (item for item in rows if item.unit_price is not None),
                key=lambda item: item.unit_price or float("inf"),
            )
        if not rows:
            answer = f"No matching advertised listing was found in this snapshot. {DATA_LABEL}."
        else:
            selected = rows if intent in {"compare_stores", "biggest_discount"} else rows[:1]
            if intent == "unit_price":
                answer = " ".join(
                    f"{item.item_name}: KES {item.unit_price:g} per {item.unit} "
                    f"at {item.supermarket} (advertised price KES {item.price_kes:g}). "
                    f"{item.product_url}"
                    for item in selected
                )
            else:
                answer = " ".join(
                    f"{item.item_name}: KES {item.price_kes:g} at {item.supermarket}. "
                    f"{item.product_url}"
                    for item in selected
                )
            answer += f" {DATA_LABEL}."
        return _base_response(
            text,
            intent,
            confidence,
            entities,
            answer,
            (
                [
                    {
                        "name": "Kenya supermarket listing snapshot",
                        "url": rows[0].product_url,
                        "note": DATA_LABEL,
                    }
                ]
                if rows
                else []
            ),
            "Kenya supermarket listing snapshot",
            None,
            "20 Oct 2026",
            "20 Oct 2026",
        )

    commodity_row = _extract(text, "commodity") or _extract(text, "commodity_sw")
    county, unknown_county = _resolve_county(text)
    if intent == "food_inflation":
        series = get_food_inflation_response()
        answer = (
            f"Latest food inflation index: {series.summary.latest_value:g} "
            f"in {series.summary.latest_month}. This is an index, not a KES price."
        )
        return _base_response(
            text,
            intent,
            confidence,
            {},
            answer,
            [{"name": SOURCE_NAME, "url": str(SOURCE_URL), "note": "National index series"}],
            SOURCE_NAME,
            str(SOURCE_URL),
            series.series.coverage_start,
            series.series.coverage_end,
        )
    if intent == "market_price":
        if not county or not commodity_row:
            return _base_response(
                text, intent, confidence, {}, f"Name a county and commodity. {EXAMPLES}", []
            )
        if unknown_county:
            entities = {"county": "not in the snapshot", "commodity": commodity_row["canonical"]}
            return _base_response(
                text,
                intent,
                confidence,
                entities,
                "That county is not in the RTFP snapshot.",
                [
                    {
                        "name": SOURCE_NAME,
                        "url": str(SOURCE_URL),
                        "note": "Coverage is county/market limited.",
                    }
                ],
                SOURCE_NAME,
                str(SOURCE_URL),
            )
        commodity = commodity_row["canonical"]
        entities = {"county": county, "commodity": commodity}
        try:
            series = get_market_prices(county, commodity)
        except KeyError:
            series = None
        if not series or not series.observations:
            answer = f"No observations for {commodity} in {county} in the dataset."
            start = end = None
        else:
            latest = max(row.date for row in series.observations)
            latest_rows = [row for row in series.observations if row.date == latest]
            answer = " ".join(
                f"{row.price:g} KES per {row.unit.removeprefix('1 ')} "
                f"at {row.market} ({row.date:%b %Y})"
                for row in latest_rows
            )
            start, end = series.coverage_start, series.coverage_end
            answer += f" Observed coverage: {start} to {end}."
        return _base_response(
            text,
            intent,
            confidence,
            entities,
            answer,
            [
                {
                    "name": SOURCE_NAME,
                    "url": str(SOURCE_URL),
                    "note": "Observed RTFP market prices; missing months are not estimated.",
                }
            ],
            SOURCE_NAME,
            str(SOURCE_URL),
            start,
            end,
        )
    return _base_response(
        text,
        intent,
        confidence,
        entities,
        f"I can't answer that from the data I have. {EXAMPLES}",
        [],
    )
