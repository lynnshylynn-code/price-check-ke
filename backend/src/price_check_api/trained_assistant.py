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
from .listings import DATA_LABEL, Listing, get_listings, parse_pack_size, search_listings
from .market_data import (
    SOURCE_NAME,
    SOURCE_URL,
    get_food_inflation_response,
    get_market_directory,
    get_market_prices,
)
from .schemas import MarketQuestionResponse

ASSISTANT_DATA = Path(__file__).resolve().parents[2] / "data/assistant"
EXAMPLES = (
    "Try asking: ‘cheapest sugar 2kg?’, ‘beans price in Kitui’, "
    "or ‘food inflation latest’."
)
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


def _slot_mentions(question: str, slot_names: tuple[str, ...]) -> list[dict[str, str]]:
    """Return distinct slot mentions in question order, preferring longer aliases."""
    candidates: list[tuple[int, int, dict[str, str]]] = []
    normalized = question.casefold()
    for slot_name in slot_names:
        for row in _slot_values().get(slot_name, []):
            surface = row.get("surface_form", "").strip()
            if not surface:
                continue
            pattern = re.compile(rf"(?<!\w){re.escape(surface)}(?!\w)", re.IGNORECASE)
            candidates.extend(
                (match.start(), match.end(), row) for match in pattern.finditer(normalized)
            )

    selected: list[tuple[int, int, dict[str, str]]] = []
    for start, end, row in sorted(candidates, key=lambda item: (item[0], -(item[1] - item[0]))):
        if any(
            start < previous_end and previous_start < end
            for previous_start, previous_end, _ in selected
        ):
            continue
        canonical = row.get("canonical", "").strip().casefold()
        surface = row.get("surface_form", "").strip().casefold()
        if any(
            canonical and canonical == existing.get("canonical", "").strip().casefold()
            or not canonical and surface == existing.get("surface_form", "").strip().casefold()
            for _, _, existing in selected
        ):
            continue
        selected.append((start, end, row))
    return [row for _, _, row in selected]


def _resolve_all_stores(question: str) -> list[dict[str, str | None]]:
    mentions = _slot_mentions(question, ("store", "store2", "other_store"))
    if not mentions:
        return []
    available = {item.supermarket.casefold(): item.supermarket for item in get_listings()}
    resolved = []
    for mention in mentions:
        canonical = mention.get("canonical", "").strip()
        store = available.get(canonical.casefold()) if canonical else None
        resolved.append(
            {
                "surface_form": mention["surface_form"],
                "store": store,
                "display": store or mention["surface_form"],
            }
        )
    return resolved


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
    mentions = _resolve_all_stores(question)
    if mentions:
        first = mentions[0]
        return first["store"], 1.0, first["store"] is None
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


def _lookup_rows(
    intent: str,
    entities: dict[str, Any],
    product: str | None,
    product_label: str | None,
    product_score: float,
    group_term: str | None = None,
) -> list[Any]:
    """Find the listings to answer from.

    Group ids such as "milk-1l" are identifiers, not text, so they must never be used as a search
    query (search_listings needs every query word inside the listing name). Specific products are
    searched by name; generic questions use the comparable group's own listings.
    """
    store = str(entities["store"]) if entities.get("store") else None
    group_id = entities.get("group")

    def by_name() -> list[Any]:
        for query in dict.fromkeys(q for q in (product, product_label) if q):
            found = list(search_listings(str(query), store, False, None, len(get_listings())))
            if found:
                return found
        return []

    def by_group() -> list[Any]:
        if not group_id:
            return []
        group = next((g for g in get_comparable_groups() if g.id == group_id), None)
        if group is None:
            return []
        members = [
            item
            for item in group.listings
            if not store or item.supermarket.casefold() == store.casefold()
        ]
        return sorted(members, key=lambda item: (item.price_kes, item.supermarket))

    def by_term() -> list[Any]:
        if not group_term:
            return []
        return list(search_listings(group_term, store, False, None, len(get_listings())))

    specific = product is not None and product_score >= 0.999
    if intent == "price_at_store" or specific:
        return by_name() or by_group() or by_term()
    if intent == "cheapest_item":
        return by_term() or by_group() or by_name()
    return by_group() or by_term() or by_name()


def _comparison_items(
    question: str,
    product: str | None,
    product_label: str | None,
    product_score: float,
    group_row: dict[str, str] | None,
) -> list[Listing]:
    if product and _extract(question, "product"):
        return _lookup_rows("compare_stores", {}, product, product_label, product_score)
    if group_row:
        group_id = group_row.get("canonical", "")
        group = next((item for item in get_comparable_groups() if item.id == group_id), None)
        if group and group.listings:
            combined = list(group.listings)
            term = group_row.get("surface_form")
            if term:
                combined.extend(search_listings(term, limit=len(get_listings())))
            return list({item.id: item for item in combined}.values())
        term = group_row.get("surface_form")
        if term:
            results = list(search_listings(term, limit=len(get_listings())))
            if results:
                return results
    return _lookup_rows("compare_stores", {}, product, product_label, product_score)


def _unit_basis(rows: list[Listing]) -> str | None:
    if not rows:
        return None
    units = {item.unit for item in rows}
    if len(units) == 1 and None not in units and all(item.unit_price is not None for item in rows):
        return "unit_price"
    sizes = [parse_pack_size(item.pack_size) for item in rows]
    if sizes[0] is not None and all(size == sizes[0] for size in sizes):
        return "pack_price"
    return None


def _same_pack_size(rows: list[Listing]) -> bool:
    sizes = [parse_pack_size(item.pack_size) for item in rows]
    return bool(sizes and sizes[0] is not None and all(size == sizes[0] for size in sizes))


def _choose_per_store(
    rows: list[Listing], stores: list[str]
) -> tuple[dict[str, Listing], str | None]:
    basis = _unit_basis(rows)
    chosen: dict[str, Listing] = {}
    for store in stores:
        candidates = [item for item in rows if item.supermarket.casefold() == store.casefold()]
        if not candidates:
            continue

        def ranking(item: Listing) -> tuple[float, float | str]:
            if basis == "unit_price":
                return float(item.unit_price or float("inf")), item.price_kes
            return item.price_kes, item.supermarket.casefold()

        chosen[store] = min(candidates, key=ranking)
    selected_basis = _unit_basis(list(chosen.values()))
    return chosen, selected_basis or basis


def _listing_line(item: Listing) -> str:
    pack = item.pack_size or "pack size unavailable"
    unit_text = (
        f"; KES {item.unit_price:g} per {item.unit}"
        if item.unit_price is not None and item.unit
        else ""
    )
    return (
        f"{item.supermarket}: {item.item_name}, KES {item.price_kes:g}, {pack}"
        f"{unit_text}; {item.product_url}"
    )


def _format_unit_price(item: Listing) -> str:
    if item.unit_price is None or item.unit is None:
        return ""
    return f"; KES {item.unit_price:g} per {item.unit}"


def _price_comparison(
    stores: list[dict[str, str | None]],
    rows: list[Listing],
    basket_items: list[tuple[str, list[Listing]]] | None = None,
) -> tuple[str, list[Listing]]:
    requested = (
        [
            (str(entry["display"]), str(entry["store"]) if entry.get("store") else None)
            for entry in stores
        ]
        if stores
        else [(name, name) for name in sorted({item.supermarket for item in get_listings()})]
    )
    requested_stores = [canonical for _, canonical in requested if canonical]
    if basket_items:
        chosen_items = [
            (label, *_choose_per_store(item_rows, requested_stores))
            for label, item_rows in basket_items
        ]
        answers: list[str] = []
        totals: dict[str, float] = {}
        all_present = True
        comparable_packs = all(
            _same_pack_size(list(chosen.values())) for _, chosen, _ in chosen_items
        )
        used_rows: list[Listing] = []
        for display_name, canonical_store in requested:
            details = []
            total = 0.0
            missing = []
            for label, chosen, _basis in chosen_items:
                item = chosen.get(canonical_store) if canonical_store else None
                if item is None:
                    missing.append(label)
                else:
                    total += item.price_kes
                    details.append(f"{label}: {_listing_line(item)}")
                    used_rows.append(item)
            if missing:
                all_present = False
                if canonical_store:
                    answers.append(
                        f"{display_name}: missing {', '.join(missing)}; no complete basket total."
                    )
                else:
                    answers.append(f"{display_name}: not in the snapshot.")
            else:
                totals[display_name] = total
                answers.append(
                    f"{display_name} basket total: KES {total:g}; " + " | ".join(details)
                )
        if len(totals) >= 2:
            if comparable_packs:
                low_store, low_total = min(totals.items(), key=lambda entry: entry[1])
                high_total = max(totals.values())
                if high_total > low_total:
                    difference = high_total - low_total
                    percent = difference / high_total * 100
                    answers.append(
                        f"{low_store} is cheaper for this basket by KES {difference:.2f} "
                        f"({percent:.2f}%)."
                    )
                else:
                    answers.append("The basket totals are equal.")
            else:
                answers.append(
                    "Pack sizes differ; basket totals are not like-for-like, "
                    "so no cheaper store is declared."
                )
        elif not all_present:
            answers.append("A store is missing an item, so its basket cannot be compared.")
        return "\n".join(answers) + f"\n{DATA_LABEL}.", used_rows

    chosen, basis = _choose_per_store(rows, requested_stores)
    answers = []
    used_rows = []
    for display_name, canonical_store in requested:
        item = chosen.get(canonical_store) if canonical_store else None
        if item:
            answers.append(_listing_line(item))
            used_rows.append(item)
        elif not canonical_store:
            answers.append(f"{display_name}: not in the snapshot.")
        else:
            answers.append(f"{display_name}: no matching listing in this snapshot.")
    if len(chosen) >= 2:
        if basis in {"unit_price", "pack_price"}:
            def comparison_value(item: Listing) -> float:
                return float(item.unit_price if basis == "unit_price" else item.price_kes)

            cheapest_store, cheapest = min(
                chosen.items(), key=lambda entry: comparison_value(entry[1])
            )
            highest = max(chosen.values(), key=comparison_value)
            low_value = comparison_value(cheapest)
            high_value = comparison_value(highest)
            unit = f" per {cheapest.unit}" if basis == "unit_price" else " for the same pack"
            if high_value > low_value:
                difference = high_value - low_value
                percent = difference / high_value * 100
                answers.append(
                    f"{cheapest_store} is cheaper by KES {difference:.2f}{unit} "
                    f"({percent:.2f}%)."
                )
            else:
                answers.append("The comparable prices are equal.")
        else:
            answers.append("Pack sizes differ; no winner is declared from absolute pack prices.")
    return "\n".join(answers) + f"\n{DATA_LABEL}.", used_rows


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

    store_mentions = _resolve_all_stores(text)
    if store_mentions:
        store = store_mentions[0]["store"]
        store_similarity = 1.0
        unknown_store = store is None
    else:
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
    if store_mentions:
        entities["stores"] = [entry["store"] or "not in the snapshot" for entry in store_mentions]
        entities["store"] = store or "not in the snapshot"
        entities["store_similarity"] = round(store_similarity, 4)
    elif store is not None or unknown_store:
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
        group_term = group_row["surface_form"] if group_row else None
        group_mentions = _slot_mentions(text, ("group", "group2"))
        unique_group_mentions: list[dict[str, str]] = []
        seen_groups: set[str] = set()
        for mention in group_mentions:
            identity = mention.get("canonical", "") or mention["surface_form"].casefold()
            if identity not in seen_groups:
                unique_group_mentions.append(mention)
                seen_groups.add(identity)
        identified = (
            product is not None or bool(entities.get("group")) or bool(group_term)
            or bool(unique_group_mentions)
        ) and not unknown_product
        if unknown_store and intent != "compare_stores":
            return _base_response(
                text,
                intent,
                confidence,
                entities,
                f"That product or store is not in the snapshot. {DATA_LABEL}.",
                [],
            )
        if intent == "compare_stores" and identified:
            if len(unique_group_mentions) > 1:
                basket_items = [
                    (
                        mention["surface_form"],
                        _comparison_items(text, None, None, 0.0, mention),
                    )
                    for mention in unique_group_mentions
                ]
                rows = [item for _, item_rows in basket_items for item in item_rows]
                answer, selected_rows = _price_comparison(store_mentions, rows, basket_items)
            else:
                rows = _comparison_items(text, product, product_label, product_score, group_row)
                answer, selected_rows = _price_comparison(store_mentions, rows)
            return _base_response(
                text,
                intent,
                confidence,
                entities,
                answer,
                [
                    {
                        "name": "Kenya supermarket listing snapshot",
                        "url": item.product_url,
                        "note": DATA_LABEL,
                    }
                    for item in selected_rows
                ],
                "Kenya supermarket listing snapshot",
                None,
                "20 Oct 2026",
                "20 Oct 2026",
            )
        if unknown_store or not identified:
            return _base_response(
                text,
                intent,
                confidence,
                entities,
                f"That product or store is not in the snapshot. {DATA_LABEL}.",
                [],
            )
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
            rows = _lookup_rows(
                intent, entities, product, product_label, product_score, group_term
            )
        if intent == "unit_price":
            rows = sorted(
                (item for item in rows if item.unit_price is not None),
                key=lambda item: item.unit_price or float("inf"),
            )
        if intent == "cheapest_item" and _unit_basis(rows) == "unit_price":
            rows = sorted(rows, key=lambda item: item.unit_price or float("inf"))
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
                if intent == "cheapest_item":
                    answer = " ".join(
                        f"{item.item_name}: KES {item.price_kes:g} at {item.supermarket} "
                        f"({item.pack_size or 'pack size unavailable'}"
                        f"{_format_unit_price(item)}). {item.product_url}"
                        for item in selected
                    )
                    if _unit_basis(rows) is None:
                        answer += " Pack sizes differ; shelf prices are not unit-price comparable."
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
