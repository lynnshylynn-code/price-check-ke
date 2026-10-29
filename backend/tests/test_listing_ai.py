import json

import pytest

from price_check_api import market_tools
from price_check_api.listing_evals import listing_eval_cases

CASES = listing_eval_cases()


def _rows(payload: dict) -> list[dict]:
    if payload.get("item"):
        return [payload["item"]]
    return [*payload.get("listings", []), *payload.get("results", [])]


def _assert_expected_data(case: dict, payload: dict) -> None:
    expected = case["expected_data"]
    if "message" in expected:
        assert payload["message"] == expected["message"]
        assert payload["results"] == []
        return
    assert any(
        all(row.get(key) == value for key, value in expected.items()) for row in _rows(payload)
    )


@pytest.mark.parametrize("case", CASES, ids=lambda case: case["id"])
def test_listing_assistant_golden_facts_use_deterministic_snapshot_tools(case: dict) -> None:
    result = market_tools.execute_market_tool(case["tool_name"], json.dumps(case["arguments"]))
    payload = json.loads(result)
    _assert_expected_data(case, payload)
    assert "snapshot 2026-10-20" in payload["data_label"]


@pytest.mark.parametrize("case", CASES[:3], ids=lambda case: case["id"])
def test_assistant_expected_facts_are_backed_by_snapshot_tool_output(case: dict) -> None:
    result = market_tools.execute_market_tool(case["tool_name"], json.dumps(case["arguments"]))
    payload = json.loads(result)
    _assert_expected_data(case, payload)
    rows = _rows(payload)
    assert rows
    assert all(row.get("product_url", "").startswith("https://") for row in rows)
