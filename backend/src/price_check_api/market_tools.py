import json
from datetime import date
from typing import Any

from pydantic import ValidationError

from .listing_groups import get_comparable_group
from .listings import (
    DATA_CAVEATS,
    DATA_LABEL,
    get_listing,
    get_listings,
    listing_dict,
    search_listings,
)
from .market_data import get_market_prices
from .schemas import (
    ToolCompareGroupArgs,
    ToolCompareMarketsArgs,
    ToolGetListingArgs,
    ToolGetSeriesArgs,
    ToolSearchListingsArgs,
)

TOOL_DEFINITIONS: list[dict[str, Any]] = [
    {
        "type": "function",
        "name": "get_series",
        "description": (
            "Read observed monthly prices for one dataset market/county and commodity. "
            "Use exact market/county names from the dataset; missing observations are omitted."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "market": {"type": "string", "description": "Exact county or market name."},
                "commodity": {"type": "string", "enum": ["beans", "maize", "goat"]},
                "from": {"type": ["string", "null"], "description": "Inclusive YYYY-MM-DD date."},
                "to": {"type": ["string", "null"], "description": "Inclusive YYYY-MM-DD date."},
            },
            "required": ["market", "commodity", "from", "to"],
            "additionalProperties": False,
        },
        "strict": True,
    },
    {
        "type": "function",
        "name": "compare_markets",
        "description": (
            "Read and compare observed prices for the same commodity across multiple exact "
            "dataset market/county names. Never estimate missing observations."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "markets": {
                    "type": "array",
                    "items": {"type": "string"},
                    "minItems": 2,
                    "maxItems": 8,
                },
                "commodity": {"type": "string", "enum": ["beans", "maize", "goat"]},
                "from": {"type": ["string", "null"], "description": "Inclusive YYYY-MM-DD date."},
                "to": {"type": ["string", "null"], "description": "Inclusive YYYY-MM-DD date."},
            },
            "required": ["markets", "commodity", "from", "to"],
            "additionalProperties": False,
        },
        "strict": True,
    },
    {
        "type": "function",
        "name": "search_listings",
        "description": "Search exact advertised product listings from the 20 Oct 2026 snapshot.",
        "parameters": {
            "type": "object",
            "properties": {
                "q": {"type": "string", "minLength": 1, "maxLength": 120},
                "store": {"type": ["string", "null"]},
                "grocery_only": {"type": "boolean"},
                "max_price": {"type": ["number", "null"], "minimum": 0},
                "limit": {"type": "integer", "minimum": 1, "maximum": 10},
            },
            "required": ["q", "store", "grocery_only", "max_price", "limit"],
            "additionalProperties": False,
        },
        "strict": True,
    },
    {
        "type": "function",
        "name": "get_listing",
        "description": "Read one listing by its exact snapshot identifier.",
        "parameters": {
            "type": "object",
            "properties": {"id": {"type": "string", "minLength": 1, "maxLength": 40}},
            "required": ["id"],
            "additionalProperties": False,
        },
        "strict": True,
    },
    {
        "type": "function",
        "name": "compare_group",
        "description": "Compare observed listings in one exact-match or staple substitute group.",
        "parameters": {
            "type": "object",
            "properties": {"group_id": {"type": "string", "minLength": 1, "maxLength": 80}},
            "required": ["group_id"],
            "additionalProperties": False,
        },
        "strict": True,
    },
]


def _parse_optional_date(value: date | None) -> date | None:
    return value


def _series_data(
    market: str,
    commodity: str,
    from_date: date | None,
    to_date: date | None,
) -> dict[str, Any]:
    response = get_market_prices(
        market,
        commodity,
        _parse_optional_date(from_date),
        _parse_optional_date(to_date),
    )
    return response.model_dump(mode="json")


def _listing_tool(name: str, arguments: str) -> dict[str, Any]:
    if name == "search_listings":
        params = ToolSearchListingsArgs.model_validate_json(arguments)
        matches = search_listings(
            params.q, params.store, params.grocery_only, params.max_price, params.limit
        )
        return {
            "data_label": DATA_LABEL,
            "caveats": DATA_CAVEATS,
            "results": [listing_dict(item) for item in matches],
            "message": None if matches else "not in the snapshot",
        }
    if name == "get_listing":
        params = ToolGetListingArgs.model_validate_json(arguments)
        item = get_listing(params.id)
        return {
            "data_label": DATA_LABEL,
            "caveats": DATA_CAVEATS,
            "item": listing_dict(item) if item else None,
            "message": None if item else "not in the snapshot",
        }
    if name == "compare_group":
        params = ToolCompareGroupArgs.model_validate_json(arguments)
        group = get_comparable_group(params.group_id)
        if group is None:
            return {"data_label": DATA_LABEL, "message": "not in the snapshot"}
        all_stores = sorted({item.supermarket for item in get_listings()})
        present_stores = {item.supermarket for item in group.listings}
        return {
            "data_label": DATA_LABEL,
            "caveats": DATA_CAVEATS,
            "group_id": group.id,
            "label": group.label,
            "basis": group.basis,
            "missing_at_stores": sorted(set(all_stores) - present_stores),
            "listings": [listing_dict(item) for item in group.listings],
        }
    raise ValueError(f"unsupported listing tool: {name}")


def execute_market_tool(name: str, arguments: str) -> str:
    try:
        if name == "get_series":
            params = ToolGetSeriesArgs.model_validate_json(arguments)
            result: dict[str, Any] = _series_data(
                params.market, params.commodity, params.from_date, params.to_date
            )
        elif name == "compare_markets":
            params = ToolCompareMarketsArgs.model_validate_json(arguments)
            result = {
                "commodity": params.commodity,
                "markets": [
                    _series_data(market, params.commodity, params.from_date, params.to_date)
                    for market in params.markets
                ],
            }
        elif name in {"search_listings", "get_listing", "compare_group"}:
            result = _listing_tool(name, arguments)
        else:
            return json.dumps({"error": f"Unsupported function '{name}'."})
    except (ValidationError, ValueError, KeyError, OverflowError) as error:
        return json.dumps({"error": str(error)})
    return json.dumps(result)
