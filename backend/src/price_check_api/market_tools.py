import json
from datetime import date
from typing import Any

from pydantic import ValidationError

from .market_data import get_market_prices
from .schemas import ToolCompareMarketsArgs, ToolGetSeriesArgs

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
        else:
            return json.dumps({"error": f"Unsupported function '{name}'."})
    except (ValidationError, ValueError, KeyError, OverflowError) as error:
        return json.dumps({"error": str(error)})
    return json.dumps(result)
