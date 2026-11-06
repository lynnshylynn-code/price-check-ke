"""Stateless, deterministic dialogue routing for the trained assistant."""

from __future__ import annotations

import csv
import json
import re
from datetime import date
from functools import lru_cache
from pathlib import Path
from typing import Any

from .listings import DATA_LABEL, get_listings
from .market_data import (
    COMMODITIES,
    SOURCE_NAME,
    SOURCE_URL,
    get_food_inflation_response,
    get_market_directory,
    get_market_price_rows,
    get_market_prices,
)
from .schemas import MarketQuestionResponse, SuggestionAction
from .trained_assistant import (
    ASSISTANT_DATA,
    MIN_PRODUCT_TOKEN_SIMILARITY,
    _classify,
    _generic_category,
    _normalize_terms,
    _product_search_text,
    _resolve_county,
    _resolve_product,
    _unknown_label,
    answer_trained_question,
    normalize_question_text,
)

MAX_CONTEXT_BYTES = 2048
MAX_TURNS = 20
MAX_LISTINGS = 5
ENTITY_KEYS = {
    "store", "other_store", "product", "group", "category", "county", "commodity", "year"
}
INTENTS = {
    "price_at_store", "cheapest_item", "compare_stores", "biggest_discount",
    "market_price", "food_inflation", "unit_price", "out_of_scope",
}
CONTEXT_KEYS = {
    "last_intent", "entities", "last_listing_ids", "offset", "pending_slot", "turn_count"
}
FOLLOW_UPS = {
    "swap_store": re.compile(r"\b(?:and at|what about|how about|at|for)\s+[^?.!]+[?!.]?$", re.I),
    "swap_product": re.compile(r"\b(?:what about|and|instead)\s+[^?.!]+[?!.]?$", re.I),
    "swap_county_or_commodity": re.compile(r"\b(?:and in|what about|in)\s+[^?.!]+[?!.]?$", re.I),
    "swap_year": re.compile(r"\b(?:and in|what about|in)\s+20\d{2}\??$", re.I),
    "show_more": re.compile(r"\b(show more|more|others|another|next)\b", re.I),
    "refine_store": re.compile(r"\b(only at|just at)\s+[^?.!]+", re.I),
    "explain": re.compile(r"\b(why|why this result|how did you get that|explain)\??$", re.I),
    "acknowledge": re.compile(r"\b(thanks|thank you|ok|okay|sawa)\b", re.I),
}
INTENT_CUE = re.compile(
    r"\b(?:cheapest|cheap|cheaper|lowest|price|prices|how much|bei ya|compare|"
    r"comparison|discount|offer|offers|deal|deals|per\s+(?:kg|kilo|litre|liter)|"
    r"inflation|market price)\b",
    re.I,
)
FOLLOW_UP_STOPWORDS = frozenset(
    {
        "a", "an", "and", "at", "about", "do", "for", "is", "it", "me", "of",
        "the", "what", "show", "more", "please",
    }
)


@lru_cache(maxsize=1)
def _known_entities() -> dict[str, set[str]]:
    result = {key: set() for key in ENTITY_KEYS}
    slots: dict[str, str] = {
        "store": "store", "store2": "store", "other_store": "store",
        "product": "product", "group": "group", "group2": "group",
        "category": "category", "county": "county",
        "commodity": "commodity", "commodity_sw": "commodity",
    }
    path = ASSISTANT_DATA / "assistant_slot_values.csv"
    with path.open(encoding="utf-8", newline="") as stream:
        for row in csv.DictReader(stream):
            entity = slots.get(row.get("slot", ""))
            if entity:
                result[entity].update(
                    value.strip().casefold()
                    for value in (row.get("canonical"), row.get("surface_form"))
                    if value and value.strip()
                )
    result["store"].update(item.supermarket.casefold() for item in get_listings())
    result["other_store"].update(result["store"])
    result["product"].update(item.item_name.casefold() for item in get_listings())
    counties, _ = get_market_directory()
    result["county"].update(value.casefold() for value in counties)
    result["commodity"].update(COMMODITIES)
    result["year"].update(str(item.year) for item in get_food_inflation_response().observations)
    result["year"].update(
        str(row.observation_date.year) for row in get_market_price_rows()
    )
    return result


@lru_cache(maxsize=1)
def _entity_surfaces() -> dict[str, dict[str, str]]:
    entity_slots = {
        "product": "product",
        "group": "group",
        "category": "category",
    }
    surfaces: dict[str, dict[str, str]] = {key: {} for key in entity_slots}
    with (ASSISTANT_DATA / "assistant_slot_values.csv").open(
        encoding="utf-8", newline=""
    ) as stream:
        for row in csv.DictReader(stream):
            entity = entity_slots.get(row.get("slot", ""))
            canonical = row.get("canonical", "").strip().casefold()
            surface = row.get("surface_form", "").strip()
            if entity and canonical and surface:
                surfaces[entity].setdefault(canonical, surface)
    return surfaces


def _entity_surface(entity: str, value: Any) -> str:
    normalized = str(value).strip().casefold()
    return _entity_surfaces().get(entity, {}).get(normalized, str(value))


def validate_context(value: Any) -> dict[str, Any]:
    """Drop unknown keys; reject the whole context if its size or known values are invalid."""
    if not isinstance(value, dict):
        return {}
    try:
        if len(json.dumps(value, ensure_ascii=False).encode("utf-8")) > MAX_CONTEXT_BYTES:
            return {}
        context = {key: item for key, item in value.items() if key in CONTEXT_KEYS}
        if not context:
            return {}
        intent = context.get("last_intent")
        if intent is not None and (not isinstance(intent, str) or intent not in INTENTS):
            return {}
        entities = context.get("entities", {})
        if not isinstance(entities, dict):
            return {}
        clean_entities: dict[str, str] = {}
        known = _known_entities()
        for key, raw in entities.items():
            if key not in ENTITY_KEYS:
                continue
            if not isinstance(raw, str) or raw.casefold() not in known[key]:
                return {}
            clean_entities[key] = raw
        ids = context.get("last_listing_ids", [])
        if not isinstance(ids, list) or len(ids) > MAX_LISTINGS:
            return {}
        available_ids = {item.id for item in get_listings()}
        if any(
            not isinstance(identifier, str) or identifier not in available_ids
            for identifier in ids
        ):
            return {}
        offset = context.get("offset", 0)
        turns = context.get("turn_count", 0)
        if not isinstance(offset, int) or not 0 <= offset <= 1000:
            return {}
        if not isinstance(turns, int) or turns < 0:
            return {}
        pending = context.get("pending_slot")
        if pending is not None and pending not in ENTITY_KEYS:
            return {}
        return {
            "last_intent": intent,
            "entities": clean_entities,
            "last_listing_ids": ids,
            "offset": offset,
            "pending_slot": pending,
            "turn_count": min(turns, MAX_TURNS),
        }
    except (TypeError, ValueError):
        return {}


@lru_cache(maxsize=1)
def _load_follow_up_classifier() -> tuple[Any, float] | None:
    model_path = Path(__file__).resolve().parents[2] / "models/followup_pipeline.joblib"
    if not model_path.is_file():
        return None
    try:
        import joblib

        metadata_path = model_path.with_name("followup_metadata.json")
        metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
        return joblib.load(model_path), float(metadata["confidence_threshold"])
    except (OSError, ValueError, KeyError, TypeError, ImportError):
        return None


def _follow_up_type(question: str, context: dict[str, Any]) -> str | None:
    if not context.get("last_intent") or context["turn_count"] >= MAX_TURNS:
        return None
    question = normalize_question_text(question)
    if INTENT_CUE.search(question):
        return None
    intent = context["last_intent"]
    content_words = [
        word for word in re.findall(r"[a-z0-9]+", question.casefold())
        if word not in FOLLOW_UP_STOPWORDS
    ]
    short_follow_up = len(content_words) <= 4
    for label in ("acknowledge", "explain", "show_more", "refine_store"):
        if short_follow_up and FOLLOW_UPS[label].search(question.strip()):
            if label == "refine_store" and intent in {"food_inflation", "market_price"}:
                return None
            return label
    if short_follow_up and intent not in {"food_inflation", "market_price"} and _slot_match(
        question, "store"
    ):
        return "swap_store"
    if short_follow_up and intent in {"food_inflation", "market_price"} and _slot_match(
        question, "year"
    ):
        return "swap_year"
    if short_follow_up and intent == "market_price" and (
        _slot_match(question, "county") or _slot_match(question, "commodity")
    ):
        return "swap_county_or_commodity"
    if short_follow_up and intent not in {"food_inflation", "market_price"} and (
        _slot_match(question, "product")
        or _slot_match(question, "group")
        or _slot_match(question, "category")
    ):
        return "swap_product"
    model_state = _load_follow_up_classifier()
    if model_state is not None:
        try:
            pipeline, model_threshold = model_state
            text = question.casefold()
            tags = []
            for slot, tag in (("store", "HAS_STORE"), ("product", "HAS_PRODUCT"),
                              ("county", "HAS_COUNTY")):
                if any(re.search(rf"(?<!\w){re.escape(value)}(?!\w)", text)
                       for value in _known_entities()[slot]):
                    tags.append(tag)
            if re.search(r"\b20\d{2}\b", text):
                tags.append("HAS_YEAR")
            if len(text.split()) <= 5:
                tags.append("IS_SHORT")
            probabilities = pipeline.predict_proba([text + " " + " ".join(tags)])[0]
            index = int(probabilities.argmax())
            if float(probabilities[index]) >= max(
                0.80, model_threshold
            ):
                label = str(pipeline.classes_[index])
                if label != "new_question":
                    if label in {"swap_store", "refine_store", "swap_product"} and intent in {
                        "food_inflation", "market_price"
                    }:
                        return None
                    if label in {"swap_county_or_commodity", "swap_year"} and intent not in {
                        "food_inflation", "market_price"
                    }:
                        return None
                    return label
                return None
        except (OSError, ValueError, KeyError, TypeError, ImportError):
            pass
    explicit = ("acknowledge", "explain", "show_more", "refine_store")
    for label in explicit:
        if short_follow_up and FOLLOW_UPS[label].search(question.strip()):
            return label
    if short_follow_up and intent in {"food_inflation", "market_price"} and _slot_match(
        question, "year"
    ):
        return "swap_year"
    if short_follow_up and _slot_match(question, "store"):
        return "swap_store"
    if short_follow_up and intent == "market_price" and (
        _slot_match(question, "county") or _slot_match(question, "commodity")
    ):
        return "swap_county_or_commodity"
    if short_follow_up and intent not in {"food_inflation", "market_price"} and (
        _slot_match(question, "product")
        or _slot_match(question, "group")
        or _slot_match(question, "category")
    ):
        return "swap_product"
    for label, pattern in FOLLOW_UPS.items():
        if not short_follow_up:
            continue
        if label in explicit:
            continue
        if label in {"swap_year", "swap_county_or_commodity"} and intent not in {
            "food_inflation", "market_price"
        }:
            continue
        if pattern.search(question.strip()):
            return label
    return None


def _merged_question(
    question: str,
    context: dict[str, Any],
    follow_up: str,
) -> tuple[str, dict[str, Any]]:
    entities = dict(context.get("entities", {}))
    offset = int(context.get("offset", 0))
    text = question.strip().rstrip("?.!")
    if follow_up == "swap_store":
        store = _slot_match(text, "store")
        if store:
            previous_store = entities.get("store")
            if previous_store and str(previous_store).casefold() != store.casefold():
                entities["other_store"] = previous_store
            entities["store"] = store
    elif follow_up == "swap_product":
        product = _slot_match(text, "product") or _slot_match(text, "group")
        if product:
            entities.pop("product", None)
            entities.pop("group", None)
            entities["product" if _slot_match(text, "product") else "group"] = product
    elif follow_up == "swap_county_or_commodity":
        county = _slot_match(text, "county")
        commodity = _slot_match(text, "commodity")
        if county:
            entities["county"] = county
        if commodity:
            entities["commodity"] = commodity
    elif follow_up == "swap_year":
        match = re.search(r"\b(20\d{2})\b", text)
        if match:
            entities["year"] = match.group(1)
    elif follow_up == "refine_store":
        store = _slot_match(text, "store")
        if store:
            entities["store"] = store
    elif follow_up == "show_more":
        offset += 1 if intent_is_single_result(context) and offset == 0 else 5
    intent = str(context["last_intent"])
    if intent == "market_price":
        merged = f"{entities.get('commodity', '')} price in {entities.get('county', '')}"
    elif intent == "food_inflation":
        merged = f"food inflation in {entities.get('year', '')}".strip()
    else:
        terms = [
            _entity_surface(key, entities[key])
            for key in ("product", "group", "category")
            if entities.get(key)
        ]
        store_term = f" at {entities['store']}" if entities.get("store") else ""
        action = {
            "price_at_store": "price of",
            "cheapest_item": "cheapest",
            "biggest_discount": "deals on",
            "unit_price": "unit price of",
            "compare_stores": "compare prices of",
        }.get(intent, "price of")
        merged = f"{action} {' '.join(terms)}{store_term}".strip()
        if follow_up == "show_more" and intent == "cheapest_item":
            merged = f"cheapest {' '.join(terms)}"
    return merged, {"last_intent": intent, "entities": entities, "offset": offset}


def intent_is_single_result(context: dict[str, Any]) -> bool:
    return context.get("last_intent") in {"cheapest_item", "unit_price", "price_at_store"}


def _slot_match(text: str, slot: str) -> str | None:
    known = _known_entities()[slot]
    candidates = sorted(known, key=len, reverse=True)
    text = _normalize_terms(normalize_question_text(text))
    return next(
        (
            value for value in candidates
            if re.search(rf"(?<!\w){re.escape(value)}(?!\w)", text, re.I)
        ),
        None,
    )


def _unknown_store_mention(text: str) -> str | None:
    match = re.search(r"\b(?:only\s+at|at)\s+([a-z][a-z0-9-]*)", text, re.I)
    if match and not _slot_match(match.group(1), "store"):
        return match.group(1)
    return None


def _is_new_question(question: str, context: dict[str, Any]) -> bool:
    """Protect explicit, entity-complete and confidently classified questions from stale context."""
    normalized = normalize_question_text(question)
    if INTENT_CUE.search(normalized):
        return True
    named_store = _slot_match(normalized, "store")
    named_item = any(
        _slot_match(normalized, slot) for slot in ("product", "group", "category")
    ) or _generic_category(normalized) is not None
    if named_store and named_item:
        return True

    follow_up = _follow_up_type(normalized, context)
    if follow_up:
        return False

    content_words = [
        word for word in re.findall(r"[a-z0-9]+", normalized.casefold())
        if word not in FOLLOW_UP_STOPWORDS
    ]
    intent, _confidence, _error = _classify(normalized)
    if len(content_words) >= 3 and intent != "out_of_scope":
        return True
    # Unrecognized short text cannot safely inherit an earlier intent.
    return True


def _contextual_comparison(question: str, context: dict[str, Any]) -> str | None:
    entities = context.get("entities", {})
    comparison_pattern = r"\b(which (?:one )?(?:is )?(?:cheaper|lower)|which costs less)\b"
    if not re.search(comparison_pattern, question, re.I):
        return None
    product = entities.get("product") or entities.get("group")
    first_store = entities.get("other_store")
    second_store = entities.get("store")
    if not (product and first_store and second_store):
        return None
    return f"compare {product} at {first_store} and {second_store}"


def answer_dialogue(
    question: str,
    raw_context: Any = None,
    follow_up_action: str | None = None,
    store: str | None = None,
) -> MarketQuestionResponse:
    question = normalize_question_text(question)
    context = validate_context(raw_context)
    if follow_up_action and not context.get("last_intent"):
        return MarketQuestionResponse(
            answer="Ask a question first, then I can explain it or show more.",
            source_name="Price Check KE data snapshots", source_url=None,
            coverage_start=None, coverage_end=None, intent="out_of_scope",
            intent_confidence=1.0, needs_clarification=False, context={},
        )
    if follow_up_action == "refine_store":
        stores = {item.supermarket.casefold(): item.supermarket for item in get_listings()}
        resolved_store = stores.get((store or "").casefold())
        if not resolved_store:
            label = _unknown_label(f"at {store or ''}")
            return MarketQuestionResponse(
                answer=f"{label} is not in the snapshot. {DATA_LABEL}.",
                source_name="Kenya supermarket listing snapshot", source_url=None,
                coverage_start="20 Oct 2026", coverage_end="20 Oct 2026",
                intent=str(context["last_intent"]), intent_confidence=1.0,
                entities=context.get("entities", {}),
            )
        context.setdefault("entities", {})["store"] = resolved_store
    if not follow_up_action:
        comparison_question = _contextual_comparison(question, context) if context else None
        if comparison_question:
            question = comparison_question
            context = {}
        elif context and _is_new_question(question, context):
            context = {}
    if context.get("pending_slot") and not follow_up_action:
        pending = context["pending_slot"]
        if pending == "product":
            resolved = (
                _slot_match(question, "product")
                or _slot_match(question, "group")
                or _slot_match(question, "category")
            )
            if not resolved:
                product, _label, score = _resolve_product(question)
                if product and score >= MIN_PRODUCT_TOKEN_SIMILARITY:
                    resolved = product
        else:
            resolved = _slot_match(question, pending)
            if pending == "county" and not resolved:
                county, is_unknown = _resolve_county(question)
                if county and not is_unknown and county.casefold() in _known_entities()["county"]:
                    resolved = county
        if resolved:
            context.setdefault("entities", {})[pending] = resolved
            context["pending_slot"] = None
            context["last_intent"] = context.get("last_intent") or "cheapest_item"
            synthesized, merged = _merged_question(question, context, "swap_product")
            merged["entities"].update(context["entities"])
            question = synthesized
            context.update(merged)
        else:
            context = {}

    follow_up = follow_up_action or _follow_up_type(question, context)
    if follow_up == "acknowledge":
        answer = MarketQuestionResponse(
            answer="You’re welcome. Ask me about prices, offers, or market data.",
            source_name="Price Check KE data snapshots", source_url=None,
            coverage_start=None, coverage_end=None, intent=str(context["last_intent"]),
            intent_confidence=1.0, entities=context.get("entities", {}),
        )
    elif follow_up == "explain":
        previous_question, _ = _merged_question("", context, "explain")
        prior = answer_trained_question(previous_question)
        source_names = ", ".join(dict.fromkeys(source.name for source in prior.sources))
        source_note = f" Sources: {source_names}." if source_names else ""
        method_sentence = (
            "I compared the available records using the dataset's listed price or unit-price "
            f"method.{source_note} {DATA_LABEL}."
        )
        source_urls = {
            str(source.url)
            for source in prior.sources
            if source.name == "Kenya supermarket listing snapshot"
        }
        cited_listings = [
            listing for listing in get_listings()
            if listing.product_url in source_urls
        ][:5]
        cited_prices = "\n".join(
            f"{listing.item_name}: KES {listing.price_kes:g} at {listing.supermarket}"
            for listing in cited_listings
        )
        explain_answer = (
            f"{cited_prices}\n{method_sentence}" if cited_prices else method_sentence
        )
        answer = MarketQuestionResponse(
            answer=explain_answer,
            source_name=prior.source_name, source_url=prior.source_url,
            coverage_start=prior.coverage_start, coverage_end=prior.coverage_end,
            sources=prior.sources, intent=str(context["last_intent"]),
            intent_confidence=1.0, entities=context.get("entities", {}),
        )
    else:
        routed_question = question
        offset = 0
        if follow_up:
            routed_question, merged = _merged_question(question, context, follow_up)
            context.update(merged)
            offset = int(context.get("offset", 0))
        unknown_store = (
            _unknown_store_mention(question)
            if follow_up in {"swap_store", "refine_store"}
            else None
        )
        if unknown_store:
            answer = MarketQuestionResponse(
                answer=f"{unknown_store.title()} is not in the snapshot. {DATA_LABEL}.",
                source_name="Kenya supermarket listing snapshot", source_url=None,
                coverage_start="20 Oct 2026", coverage_end="20 Oct 2026",
                intent=str(context["last_intent"]), intent_confidence=1.0,
            )
            context.get("entities", {}).pop("store", None)
        elif follow_up == "refine_store":
            ids = set(context.get("last_listing_ids", []))
            store = context.get("entities", {}).get("store")
            matches = [
                item for item in get_listings()
                if item.id in ids and store
                and item.supermarket.casefold() == str(store).casefold()
            ]
            if matches:
                answer = MarketQuestionResponse(
                    answer="\n".join(
                        f"{item.item_name}: KES {item.price_kes:g} at {item.supermarket} "
                        f"({item.pack_size or 'pack size unavailable'}). {item.product_url}"
                        for item in matches
                    ) + f"\n{DATA_LABEL}.",
                    source_name="Kenya supermarket listing snapshot", source_url=None,
                    coverage_start="20 Oct 2026", coverage_end="20 Oct 2026",
                    sources=[
                        {"name": "Kenya supermarket listing snapshot", "url": item.product_url,
                         "note": DATA_LABEL}
                        for item in matches
                    ],
                    intent=str(context["last_intent"]), intent_confidence=1.0,
                    entities=context.get("entities", {}),
                )
            else:
                answer = MarketQuestionResponse(
                    answer=(f"No previous result matched {store or 'that store'} in the current "
                            f"snapshot. {DATA_LABEL}."),
                    source_name="Kenya supermarket listing snapshot", source_url=None,
                    coverage_start="20 Oct 2026", coverage_end="20 Oct 2026",
                    intent=str(context["last_intent"]), intent_confidence=1.0,
                    entities=context.get("entities", {}),
                )
        elif follow_up == "swap_year" and context.get("entities", {}).get("year") and (
            context.get("last_intent") == "food_inflation"
        ):
            series = get_food_inflation_response()
            year = int(context["entities"]["year"])
            observations = [item for item in series.observations if item.year == year]
            if observations:
                latest = max(observations, key=lambda item: item.month_number)
                answer = MarketQuestionResponse(
                    answer=(f"Food inflation index for {year}: latest reported value "
                            f"{latest.value:g}% in {latest.month} {year}; "
                            f"{len(observations)} reported monthly observations. This is an index, "
                            "not a KES price."),
                    source_name=SOURCE_NAME, source_url=str(SOURCE_URL),
                    coverage_start=series.series.coverage_start,
                    coverage_end=series.series.coverage_end,
                    sources=[{"name": SOURCE_NAME, "url": str(SOURCE_URL),
                              "note": "National historical index series"}],
                    intent="food_inflation", intent_confidence=1.0,
                )
            else:
                answer = answer_trained_question(routed_question, offset=offset)
        elif follow_up == "swap_year" and context.get("entities", {}).get("year") and (
            context.get("last_intent") == "market_price"
        ):
            year = int(context["entities"]["year"])
            series = get_market_prices(
                str(context["entities"].get("county", "")),
                str(context["entities"].get("commodity", "")),
                date(year, 1, 1),
                date(year, 12, 31),
            )
            latest_by_market = {}
            for observation in series.observations:
                current = latest_by_market.get(observation.market)
                if current is None or observation.date > current.date:
                    latest_by_market[observation.market] = observation
            if latest_by_market:
                answer = MarketQuestionResponse(
                    answer=(" ".join(
                        f"{item.price:g} KES per {item.unit.removeprefix('1 ')} at "
                        f"{item.market} ({item.date:%b %Y})"
                        for item in latest_by_market.values()
                    ) + f" Observed coverage: {series.coverage_start} to {series.coverage_end}."),
                    source_name=series.source_name, source_url=str(series.source_url),
                    coverage_start=series.coverage_start, coverage_end=series.coverage_end,
                    sources=[{"name": series.source_name, "url": str(series.source_url),
                              "note": series.source_note}],
                    intent="market_price", intent_confidence=1.0,
                    entities=context.get("entities", {}),
                )
            else:
                answer = MarketQuestionResponse(
                    answer=f"No observations for that county and commodity in {year}.",
                    source_name=series.source_name, source_url=str(series.source_url),
                    coverage_start=series.coverage_start, coverage_end=series.coverage_end,
                    sources=[{"name": series.source_name, "url": str(series.source_url),
                              "note": series.source_note}],
                    intent="market_price", intent_confidence=1.0,
                    entities=context.get("entities", {}),
                )
        else:
            answer = answer_trained_question(routed_question, offset=offset)

    intent = answer.intent
    entities = dict(context.get("entities", {}))
    if category := _slot_match(question, "category"):
        entities["category"] = category
    if follow_up in {"swap_store", "refine_store"} and _unknown_store_mention(question):
        entities.pop("store", None)
    for key in ENTITY_KEYS:
        value = answer.entities.get(key)
        if isinstance(value, str) and value.casefold() in _known_entities()[key]:
            entities[key] = value
    missing: str | None = None
    query_has_entity = any(
        entities.get(key) for key in ("product", "group", "category")
    ) or any(
        _slot_match(question, slot)
        for slot in ("product", "group", "category")
    ) or _generic_category(question) is not None
    has_listing_candidates = any(
        source.name == "Kenya supermarket listing snapshot" and source.url
        for source in answer.sources
    )
    if (
        intent in {"price_at_store", "cheapest_item"}
        and not query_has_entity
        and not has_listing_candidates
    ):
        leftover = _product_search_text(question)
        if leftover:
            answer = answer.model_copy(update={
                "answer": f"{leftover} is not in the snapshot. {DATA_LABEL}."
            })
        else:
            missing = "product"
    elif intent == "market_price" and not entities.get("county"):
        missing = "county"
    needs_clarification = missing is not None
    if missing:
        resolved_store = entities.get("store")
        snapshot_stores = {item.supermarket.casefold(): item.supermarket for item in get_listings()}
        display_store = (
            snapshot_stores.get(str(resolved_store).casefold()) if resolved_store else None
        )
        prompts = {
            "product": (
                f"Which product or group at {display_store}? For example, maize flour, beans, "
                "or milk."
                if display_store
                else "Which product or group? For example, maize flour, beans, or milk."
            ),
            "county": "Which county? For example, Nairobi, Mombasa, or Kisumu.",
        }
        answer = answer.model_copy(update={"answer": prompts[missing]})
    listing_ids: list[str] = []
    used_urls = {str(source.url) for source in answer.sources}
    for listing in get_listings():
        if listing.product_url in used_urls and listing.id not in listing_ids:
            listing_ids.append(listing.id)
            if len(listing_ids) == MAX_LISTINGS:
                break
    next_context = {
        "last_intent": intent,
        "entities": entities,
        "last_listing_ids": listing_ids,
        "offset": int(context.get("offset", 0)) if follow_up == "show_more" else 0,
        "pending_slot": missing,
        "turn_count": min(MAX_TURNS, int(context.get("turn_count", 0)) + 1),
    }
    if intent in {"cheapest_item", "unit_price", "price_at_store", "biggest_discount"}:
        suggestions = ["Show more", "Only at Naivas", "Why this result?"]
    elif intent == "market_price":
        suggestions = ["What about beans?", "And in Garissa?", "Why this result?"]
    elif intent == "food_inflation":
        suggestions = ["What about 2023?", "Average reading?", "Why this result?"]
    else:
        suggestions = ["What is the cheapest milk?", "Show current offers", "New question"]
    if intent in {"cheapest_item", "unit_price", "price_at_store", "biggest_discount"}:
        suggestion_actions = [
            SuggestionAction(label="Show more", action="show_more"),
            SuggestionAction(label="Only at Naivas", action="refine_store", store="Naivas"),
            SuggestionAction(label="Why this result?", action="explain"),
        ]
    else:
        suggestion_actions = [
            SuggestionAction(label=label, action=None) for label in suggestions
        ]
    return answer.model_copy(update={
        "context": next_context,
        "suggestions": suggestions,
        "suggestion_actions": suggestion_actions,
        "needs_clarification": needs_clarification,
        "follow_up_type": follow_up,
    })
