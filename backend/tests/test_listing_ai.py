import asyncio
import json
from types import SimpleNamespace

import pytest

from price_check_api import ai_insights, market_tools
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
        all(row.get(key) == value for key, value in expected.items())
        for row in _rows(payload)
    )


@pytest.mark.parametrize("case", CASES, ids=lambda case: case["id"])
def test_listing_ai_golden_facts_are_computed_from_csv_tools(case: dict) -> None:
    actual = market_tools.execute_market_tool(
        case["tool_name"], json.dumps(case["arguments"])
    )
    payload = json.loads(actual)
    _assert_expected_data(case, payload)
    assert "snapshot 2026-10-20" in payload["data_label"]


@pytest.mark.parametrize("case", CASES[:3], ids=lambda case: case["id"])
def test_listing_ai_uses_mocked_model_with_real_tool_output(
    case: dict, monkeypatch: pytest.MonkeyPatch
) -> None:
    tool_result = market_tools.execute_market_tool(
        case["tool_name"], json.dumps(case["arguments"])
    )
    _assert_expected_data(case, json.loads(tool_result))
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    monkeypatch.setattr(ai_insights, "execute_market_tool", market_tools.execute_market_tool)

    class FakeResponses:
        calls = 0

        async def create(self, **request: object) -> object:
            self.calls += 1
            if self.calls == 1:
                return SimpleNamespace(
                    id="listing-golden-tool-call",
                    output=[SimpleNamespace(
                        type="function_call",
                        name=case["tool_name"],
                        call_id="listing-call",
                        arguments=json.dumps(case["arguments"]),
                    )],
                    output_text="",
                )
            inputs = request["input"]
            returned = json.loads(inputs[0]["output"])
            _assert_expected_data(case, returned)
            return SimpleNamespace(
                id="listing-answer", output=[], output_text=case["expected_fact"]
            )

    responses = FakeResponses()

    class FakeClient:
        def __init__(self, **_: object) -> None:
            self.responses = responses

        async def __aenter__(self) -> "FakeClient":
            return self

        async def __aexit__(self, *_: object) -> None:
            return None

    monkeypatch.setattr(ai_insights, "AsyncOpenAI", FakeClient)
    answer = asyncio.run(ai_insights.answer_market_question(case["question"]))
    assert answer.answer == case["expected_fact"]
    assert answer.source_name == "Kenya supermarket listing snapshot"
    assert answer.coverage_start == "20 Oct 2026"
