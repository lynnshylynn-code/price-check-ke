"""Exercise the live model against fixture and CSV-derived market questions.

This is an opt-in manual evaluation; it is not part of pytest or CI.
"""

import asyncio
import json
import os
from pathlib import Path

from price_check_api.ai_insights import answer_market_question
from price_check_api.market_data import get_market_directory, get_market_prices

FIXTURES = Path(__file__).resolve().parents[1] / "tests" / "evals" / "market_qa.json"
COUNTIES = (
    "Turkana", "Kilifi", "Makueni", "Marsabit", "Mandera", "North Imenti", "Lamu West", "Voi"
)
COMMODITIES = ("beans", "maize", "goat")


def cases_from_csv() -> list[dict[str, str]]:
    _, markets = get_market_directory()
    available_counties = {option.county for option in markets if option.available_commodities}
    cases = []
    for county in COUNTIES:
        for commodity in COMMODITIES:
            if county not in available_counties:
                continue
            series = get_market_prices(county, commodity)
            if not series.observations:
                continue
            latest = max(series.observations, key=lambda row: row.date)
            unit = series.unit.removeprefix("1 ")
            cases.append({
                "id": f"live-{county.casefold().replace(' ', '-')}-{commodity}",
                "question": f"What is the latest recorded {commodity} price in {county}?",
                "expected_fact": f"{latest.price:g} KES per {unit}",
            })
    if len(cases) < 8:
        raise RuntimeError(f"Expected at least 8 available CSV-derived cases; found {len(cases)}")
    return cases


async def run() -> int:
    fixtures = json.loads(FIXTURES.read_text(encoding="utf-8"))
    live_cases = [
        {"id": case["id"], "question": case["question"], "expected_fact": case["expected_fact"]}
        for case in fixtures
    ] + cases_from_csv()
    failures = []
    for case in live_cases:
        response = await answer_market_question(case["question"])
        if case["expected_fact"].casefold() not in response.answer.casefold():
            failures.append((case["id"], case["expected_fact"], response.answer))
    passed = len(live_cases) - len(failures)
    print(f"Live model evaluation: {passed}/{len(live_cases)} ({passed / len(live_cases):.1%})")
    for case_id, expected, answer in failures:
        print(f"FAIL {case_id}: expected {expected!r}; answer={answer!r}")
    return 1 if failures else 0


if __name__ == "__main__":
    if not os.getenv("OPENAI_API_KEY"):
        print("Skipped live model evaluation: OPENAI_API_KEY is not set.")
    else:
        raise SystemExit(asyncio.run(run()))
