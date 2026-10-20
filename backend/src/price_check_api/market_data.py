import csv
from dataclasses import dataclass
from datetime import date
from functools import lru_cache
from pathlib import Path

from .schemas import (
    Commodity,
    FoodInflationResponse,
    MarketOption,
    MarketSeries,
    MarketSummary,
    Observation,
    PriceObservation,
    PriceSeriesResponse,
)

DATA_FILE = Path(__file__).resolve().parents[2] / "data" / "rtfp_kenya_market_2007_2026-08.csv"
SOURCE_URL = "https://microdata.worldbank.org/index.php/catalog/6167"
SOURCE_NAME = "World Bank Kenya Monthly Food Price Estimates by Product and Market (RTFP)"

# The catalog's file dictionary and CSV `components` field define these units;
# inflation and *_price_index fields are separate derived series, not KES prices.
COMMODITIES = {
    "beans": Commodity(code="beans", name="Beans", unit="1 kg"),
    "maize": Commodity(code="maize", name="Maize", unit="1 kg"),
    "goat": Commodity(code="goat", name="Goat", unit="1 unit"),
}
PRICE_UNITS = {
    "beans": "1 kg",
    "maize": "1 kg",
    "goat": "1 unit",
}


@dataclass(frozen=True)
class MarketPriceRow:
    market: str
    county: str
    region: str
    observation_date: date
    currency: str
    beans: float | None
    maize: float | None
    goat: float | None

    def price(self, commodity: str) -> float | None:
        return {
            "beans": self.beans,
            "maize": self.maize,
            "goat": self.goat,
        }[commodity]


def _optional_float(value: str) -> float | None:
    value = value.strip()
    return float(value) if value else None


@lru_cache(maxsize=1)
def get_market_price_rows() -> tuple[MarketPriceRow, ...]:
    rows: list[MarketPriceRow] = []
    with DATA_FILE.open(encoding="utf-8-sig", newline="") as dataset_file:
        for row in csv.DictReader(dataset_file):
            components = row["components"]
            if not (
                "beans (1 KG" in components
                and "livestock_goat_s_fao (1 unit" in components
                and "maize_fao (1 Kg" in components
            ):
                raise ValueError("RTFP component units do not match the documented price fields.")
            rows.append(
                MarketPriceRow(
                    market=row["mkt_name"].strip(),
                    county=row["adm2_name"].strip(),
                    region=row["adm1_name"].strip(),
                    observation_date=date.fromisoformat(row["price_date"]),
                    currency=row["currency"].strip(),
                    beans=_optional_float(row["beans"]),
                    maize=_optional_float(row["maize_fao"]),
                    goat=_optional_float(row["livestock_goat_s_fao"]),
                )
            )
    return tuple(rows)


@lru_cache(maxsize=1)
def get_market_directory() -> tuple[list[str], list[MarketOption]]:
    rows = get_market_price_rows()
    county_names = sorted({row.county for row in rows if row.county != "Market Average"})
    options: dict[tuple[str, str, str], set[str]] = {}
    for row in rows:
        if row.market == "Market Average" or row.county == "Market Average":
            continue
        key = (row.market, row.county, row.region)
        available = options.setdefault(key, set())
        for commodity in COMMODITIES:
            if row.price(commodity) is not None:
                available.add(commodity)
    markets = [
        MarketOption(
            name=name,
            county=county,
            region=region,
            available_commodities=sorted(available),
        )
        for (name, county, region), available in sorted(options.items())
    ]
    return county_names, markets


def get_market_prices(
    market: str,
    commodity: str,
    from_date: date | None = None,
    to_date: date | None = None,
) -> PriceSeriesResponse:
    if commodity not in COMMODITIES:
        raise ValueError(f"Unsupported commodity '{commodity}'.")

    county_names, market_options = get_market_directory()
    search_name = market.strip()
    is_county = search_name.casefold() in {county.casefold() for county in county_names}
    if is_county:
        selected_rows = [
            row for row in get_market_price_rows()
            if row.county.casefold() == search_name.casefold()
        ]
    else:
        known_names = {option.name.casefold() for option in market_options}
        if search_name.casefold() not in known_names:
            raise KeyError(f"Unknown market or county '{search_name}'.")
        selected_rows = [
            row for row in get_market_price_rows()
            if row.market.casefold() == search_name.casefold()
        ]

    unit = PRICE_UNITS[commodity]
    observations: list[PriceObservation] = []
    for row in selected_rows:
        price = row.price(commodity)
        if price is None:
            continue
        if from_date and row.observation_date < from_date:
            continue
        if to_date and row.observation_date > to_date:
            continue
        observations.append(
            PriceObservation(
                market=row.market,
                county=row.county,
                region=row.region,
                date=row.observation_date,
                commodity=commodity,
                price=price,
                currency=row.currency,
                unit=unit,
            )
        )

    observations.sort(key=lambda item: (item.date, item.market))
    if len(observations) > 5_000:
        raise OverflowError("Date range returns too many rows; narrow the requested range.")
    dates = [item.date for item in observations]
    return PriceSeriesResponse(
        market=search_name,
        commodity=commodity,
        unit=unit,
        currency="KES",
        source_name=SOURCE_NAME,
        source_url=SOURCE_URL,
        coverage_start=dates[0].isoformat() if dates else None,
        coverage_end=dates[-1].isoformat() if dates else None,
        source_note=(
            "Observed source-market prices in KES; one record per market and month. "
            "No missing values are interpolated and county selections are not averaged."
        ),
        observations=observations,
    )


@lru_cache(maxsize=1)
def get_food_inflation_response() -> FoodInflationResponse:
    observations: list[Observation] = []
    month_rows = 0
    with DATA_FILE.open(encoding="utf-8-sig", newline="") as dataset_file:
        for row in csv.DictReader(dataset_file):
            if row["mkt_name"] != "Market Average":
                continue
            month_rows += 1
            value = row["inflation_food_price_index"].strip()
            if not value:
                continue
            observation_date = date.fromisoformat(row["price_date"])
            observations.append(
                Observation(
                    year=observation_date.year,
                    month=observation_date.strftime("%b"),
                    month_number=observation_date.month,
                    value=float(value),
                )
            )

    if len(observations) < 2:
        raise ValueError("RTFP dataset must include at least two national average observations.")
    dates = [(item.year, item.month_number) for item in observations]
    if dates != sorted(dates) or len(set(dates)) != len(dates):
        raise ValueError("Food inflation observations must be ordered by month.")

    first = observations[0]
    latest = observations[-1]
    previous = observations[-2]
    peak = max(observations, key=lambda item: item.value)
    minimum = min(observations, key=lambda item: item.value)
    change = round(latest.value - previous.value, 2)
    direction = "up" if change > 0 else "down" if change < 0 else "unchanged"

    def formatted_month(item: Observation) -> str:
        return f"{item.month} {item.year}"

    series = MarketSeries(
        country="Kenya",
        market_scope="National market average",
        market_id="gid_ken_national_average",
        indicator="inflation_food_price_index",
        unit="%",
        year=latest.year,
        source_name="World Bank Kenya Monthly Food Price Estimates by Product and Market (RTFP)",
        source_url=SOURCE_URL,
        source_note=(
            f"National Market Average row from the supplied RTFP CSV: {month_rows} monthly "
            f"records, with {len(observations)} reported inflation values. "
            "The first 12 monthly inflation values are blank in the source."
        ),
        coverage_start=formatted_month(first),
        coverage_end=formatted_month(latest),
    )
    narrative = (
        f"The latest reported food-price index inflation value is {latest.value:.2f}% "
        f"for {formatted_month(latest)}, {abs(change):.2f} percentage points {direction} "
        f"from {formatted_month(previous)}. The highest value in this series was "
        f"{peak.value:.2f}% in {formatted_month(peak)}. This is historical market data, "
        "not a forecast or a supermarket price."
    )
    summary = MarketSummary(
        observation_count=len(observations),
        missing_month_count=month_rows - len(observations),
        mean_value=round(sum(item.value for item in observations) / len(observations), 2),
        minimum_month=formatted_month(minimum),
        minimum_value=minimum.value,
        latest_month=formatted_month(latest),
        latest_value=latest.value,
        previous_month=formatted_month(previous),
        previous_value=previous.value,
        change_from_previous=change,
        peak_month=formatted_month(peak),
        peak_value=peak.value,
        direction=direction,
        narrative=narrative,
    )
    return FoodInflationResponse(
        series=series,
        observations=observations,
        summary=summary,
    )
