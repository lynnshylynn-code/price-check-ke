import calendar
import re
from datetime import date

from .market_data import (
    SOURCE_NAME,
    SOURCE_URL,
    get_food_inflation_response,
    get_market_directory,
    get_market_prices,
)
from .schemas import MarketQuestionResponse

_MONTHS = {
    name.lower(): number
    for number, name in enumerate(calendar.month_name)
    if name
}
_MONTHS.update({name.lower(): number for number, name in enumerate(calendar.month_abbr) if name})


def _response(answer: str, coverage_start: str, coverage_end: str) -> MarketQuestionResponse:
    return MarketQuestionResponse(
        answer=answer,
        source_name=SOURCE_NAME,
        source_url=SOURCE_URL,
        coverage_start=coverage_start,
        coverage_end=coverage_end,
    )


def answer_question_offline(question: str) -> MarketQuestionResponse:
    normalized = question.casefold()
    if any(term in normalized for term in ("forecast", "predict", "future")):
        return _response(
            "The RTFP data is historical and does not provide a forecast.",
            "Jan 2007",
            "Aug 2026",
        )
    if any(term in normalized for term in ("supermarket", "retailer", "brand")):
        return _response(
            "The RTFP dataset contains market-level observations, not verified supermarket "
            "or brand prices. The supermarket examples in the app are demo data.",
            "Jan 2007",
            "Aug 2026",
        )

    commodity_aliases = {
        "beans": ("beans", "bean"),
        "maize": ("maize", "corn"),
        "goat": ("goat",),
    }
    commodity = next(
        (
            code
            for code, aliases in commodity_aliases.items()
            if any(re.search(rf"\b{re.escape(alias)}\b", normalized) for alias in aliases)
        ),
        None,
    )
    if commodity:
        counties, market_options = get_market_directory()
        market_names = sorted(
            {
                (option.name, option.county)
                for option in market_options
            }
            | {(county, county) for county in counties},
            key=lambda item: len(item[0]),
            reverse=True,
        )
        matched_markets: list[str] = []
        for market_name, _county in market_names:
            if (
                re.search(rf"(?<!\w){re.escape(market_name.casefold())}(?!\w)", normalized)
                and market_name.casefold() not in {item.casefold() for item in matched_markets}
            ):
                matched_markets.append(market_name)
        if not matched_markets:
            return _response(
                f"Name a dataset market or county to ask about {commodity} prices. "
                "Observed prices are in KES and are not supermarket prices.",
                "Jan 2007",
                "Aug 2026",
            )

        requested_period = re.search(
            r"\b(?P<month>january|jan|february|feb|march|mar|april|apr|may|june|jun|"
            r"july|jul|august|aug|september|sep|october|oct|november|nov|"
            r"december|dec)\s+(?P<year>(?:19|20)\d{2})\b",
            normalized,
        )
        from_date = to_date = None
        if requested_period:
            month_name = requested_period.group("month")
            year = int(requested_period.group("year"))
            month = _MONTHS[month_name]
            from_date = date(year, month, 1)
            to_date = date(year, month, calendar.monthrange(year, month)[1])

        answers: list[str] = []
        coverages: list[date] = []
        for market_name in matched_markets[:4]:
            series = get_market_prices(market_name, commodity, from_date, to_date)
            if not series.observations:
                requested = f" for {requested_period.group(0)}" if requested_period else ""
                answers.append(
                    f"No {commodity} price observations were found for {market_name}{requested}."
                )
                continue
            latest_date = max(item.date for item in series.observations)
            latest = [item for item in series.observations if item.date == latest_date]
            coverages.extend(item.date for item in series.observations)
            answers.extend(
                f"{item.price:g} KES per {item.unit.removeprefix('1 ')} at {item.market} "
                f"({item.date.strftime('%b %Y')})"
                for item in latest
            )

        if not coverages and all("No " in answer for answer in answers):
            start, end = "Jan 2007", "Aug 2026"
        else:
            start = min(coverages).strftime("%b %Y") if coverages else "Jan 2007"
            end = max(coverages).strftime("%b %Y") if coverages else "Aug 2026"
        return _response(
            " ".join(answers)
            + " These are observed market prices; missing values are not estimated.",
            start,
            end,
        )

    inflation = get_food_inflation_response()
    if any(term in normalized for term in ("average", "mean")):
        answer = (
            f"The mean national food-price inflation index was "
            f"{inflation.summary.mean_value:.2f}% across "
            f"{inflation.summary.observation_count} observations. This is not a product price."
        )
    else:
        answer = (
            f"The latest national food-price inflation index was "
            f"{inflation.summary.latest_value:.2f}% in {inflation.summary.latest_month}. "
            "This is an index reading, not a product or supermarket price."
        )
    return _response(answer, inflation.series.coverage_start, inflation.series.coverage_end)
