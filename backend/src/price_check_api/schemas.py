from datetime import date
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, HttpUrl, field_validator, model_validator


class Observation(BaseModel):
    model_config = ConfigDict(frozen=True)

    year: int
    month: str
    month_number: int
    value: float


class MarketSeries(BaseModel):
    model_config = ConfigDict(frozen=True)

    country: str
    market_scope: str
    market_id: str
    indicator: str
    unit: str
    year: int
    source_name: str
    source_url: HttpUrl
    source_note: str
    coverage_start: str
    coverage_end: str


class MarketSummary(BaseModel):
    model_config = ConfigDict(frozen=True)

    observation_count: int
    missing_month_count: int
    mean_value: float
    minimum_month: str
    minimum_value: float
    latest_month: str
    latest_value: float
    previous_month: str
    previous_value: float
    change_from_previous: float
    peak_month: str
    peak_value: float
    direction: str
    narrative: str


class FoodInflationResponse(BaseModel):
    model_config = ConfigDict(frozen=True)

    series: MarketSeries
    observations: list[Observation]
    summary: MarketSummary


class MarketQuestionRequest(BaseModel):
    question: str = Field(min_length=3, max_length=500)

    @field_validator("question")
    @classmethod
    def strip_question(cls, value: str) -> str:
        question = value.strip()
        if not question:
            raise ValueError("Question must not be blank.")
        return question


class MarketQuestionResponse(BaseModel):
    model_config = ConfigDict(frozen=True)

    answer: str
    source_name: str
    source_url: HttpUrl
    coverage_start: str
    coverage_end: str


class Commodity(BaseModel):
    code: str
    name: str
    unit: str


class MarketOption(BaseModel):
    name: str
    county: str
    region: str
    available_commodities: list[str]


class MarketDirectoryResponse(BaseModel):
    source_name: str
    source_url: HttpUrl
    commodities: list[Commodity]
    counties: list[str]
    markets: list[MarketOption]


class PriceObservation(BaseModel):
    market: str
    county: str
    region: str
    date: date
    commodity: str
    price: float
    currency: str
    unit: str


class PriceSeriesResponse(BaseModel):
    market: str
    commodity: str
    unit: str
    currency: str
    source_name: str
    source_url: HttpUrl
    coverage_start: str | None
    coverage_end: str | None
    source_note: str
    observations: list[PriceObservation]


class PricePositionResponse(BaseModel):
    market: str
    commodity: str
    source_name: str
    source_url: HttpUrl
    coverage_start: str | None
    coverage_end: str | None
    aggregation: str
    latest_date: date | None
    latest_price: float | None
    recent_trend: Literal["rising", "stable", "falling"] | None
    score: float | None
    label: Literal["low", "typical", "high"] | None
    reason: str
    p10: float | None
    p50: float | None
    p90: float | None
    memberships: dict[str, float] | None


class DemoStorePrice(BaseModel):
    store: str
    price: float
    stock: str


class DemoProduct(BaseModel):
    id: str
    name: str
    size: str
    description: str
    category: str
    prices: list[DemoStorePrice]


class ProductCatalogResponse(BaseModel):
    is_demo_data: Literal[True] = True
    disclaimer: str
    products: list[DemoProduct]


class BasketLineRequest(BaseModel):
    product_id: str = Field(min_length=1, max_length=80)
    quantity: int = Field(ge=1, le=1000)


class BasketPricingRequest(BaseModel):
    items: list[BasketLineRequest] = Field(min_length=1, max_length=100)
    strategy: Literal["lowest", "single"] = "lowest"


class BasketPricedLine(BaseModel):
    product_id: str
    product_name: str
    quantity: int
    store: str
    unit_price: float
    total: float


class BasketStoreTotal(BaseModel):
    store: str
    total: float


class BasketPricingResponse(BaseModel):
    is_demo_data: Literal[True] = True
    disclaimer: str
    strategy: Literal["lowest", "single"]
    best_single_store: str | None
    store_totals: list[BasketStoreTotal]
    total: float
    lines: list[BasketPricedLine]


class BasketOptimizeRequest(BaseModel):
    product_ids: list[str] = Field(min_length=1, max_length=8)
    trip_cost: float = Field(default=0, ge=0, allow_inf_nan=False)
    strategy: Literal["bfs", "ucs", "astar"] = "astar"

    @field_validator("product_ids")
    @classmethod
    def unique_product_ids(cls, value: list[str]) -> list[str]:
        if len(set(value)) != len(value):
            raise ValueError("product_ids must be unique")
        return value


class BasketSearchAssignment(BaseModel):
    product_id: str
    store: str


class BasketOptimizeResponse(BaseModel):
    is_demo_data: Literal[True] = True
    disclaimer: str
    strategy: Literal["bfs", "ucs", "astar"]
    total_cost: float
    nodes_expanded: int
    assignments: list[BasketSearchAssignment]


class ToolGetSeriesArgs(BaseModel):
    market: str = Field(min_length=1, max_length=120)
    commodity: Literal["beans", "maize", "goat"]
    from_date: date | None = Field(alias="from")
    to_date: date | None = Field(alias="to")
    model_config = ConfigDict(frozen=True, populate_by_name=True, extra="forbid")

    @model_validator(mode="after")
    def validate_date_order(self) -> "ToolGetSeriesArgs":
        if self.from_date and self.to_date and self.to_date < self.from_date:
            raise ValueError("'to' must be on or after 'from'.")
        return self


class ToolCompareMarketsArgs(BaseModel):
    markets: list[str] = Field(min_length=2, max_length=8)
    commodity: Literal["beans", "maize", "goat"]
    from_date: date | None = Field(alias="from")
    to_date: date | None = Field(alias="to")
    model_config = ConfigDict(frozen=True, populate_by_name=True, extra="forbid")

    @model_validator(mode="after")
    def validate_date_order(self) -> "ToolCompareMarketsArgs":
        if self.from_date and self.to_date and self.to_date < self.from_date:
            raise ValueError("'to' must be on or after 'from'.")
        return self
