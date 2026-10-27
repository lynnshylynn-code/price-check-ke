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
    question: str = Field(min_length=3, max_length=300)

    @field_validator("question")
    @classmethod
    def strip_question(cls, value: str) -> str:
        if any(ord(char) < 32 and char not in "\t\n\r" for char in value):
            raise ValueError("Question must not contain control characters.")
        question = value.strip()
        if not question:
            raise ValueError("Question must not be blank.")
        return question


class AssistantAskRequest(BaseModel):
    question: str = Field(min_length=1, max_length=300)

    @field_validator("question")
    @classmethod
    def validate_question(cls, value: str) -> str:
        if any(ord(char) < 32 and char not in "\t\n\r" for char in value):
            raise ValueError("Question must not contain control characters.")
        question = value.strip()
        if not question:
            raise ValueError("Question must not be blank.")
        return question


class MarketAnswerSource(BaseModel):
    name: str
    url: HttpUrl
    note: str


class MarketQuestionResponse(BaseModel):
    model_config = ConfigDict(frozen=True)

    answer: str
    source_name: str
    source_url: HttpUrl | None
    coverage_start: str | None
    coverage_end: str | None
    sources: list[MarketAnswerSource] = Field(default_factory=list)
    intent: str = "out_of_scope"
    intent_confidence: float = 0.0
    entities: dict[str, object] = Field(default_factory=dict)
    model_version: str = "unavailable"


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
    product_ids: list[str] | None = Field(default=None, min_length=1, max_length=8)
    group_ids: list[str] | None = Field(default=None, min_length=1, max_length=20)
    quantities: list[int] | None = None
    trip_cost: float = Field(default=0, ge=0, allow_inf_nan=False)
    strategy: Literal["bfs", "ucs", "astar"] = "astar"

    @model_validator(mode="after")
    def validate_selection(self) -> "BasketOptimizeRequest":
        if bool(self.product_ids) == bool(self.group_ids):
            raise ValueError("provide exactly one of product_ids or group_ids")
        identifiers = self.product_ids or self.group_ids or []
        if len(set(identifiers)) != len(identifiers):
            raise ValueError("selected identifiers must be unique")
        if self.quantities is not None:
            if self.group_ids is None or len(self.quantities) != len(self.group_ids):
                raise ValueError("quantities must match group_ids")
            if any(quantity < 1 or quantity > 20 for quantity in self.quantities):
                raise ValueError("quantities must be between 1 and 20")
        return self


class BasketSearchAssignment(BaseModel):
    product_id: str
    store: str


class BasketOptimizedLine(BaseModel):
    group_id: str
    item_name: str
    listing_id: str
    store: str
    quantity: int
    price_kes: float
    unit_price: float | None
    line_total_kes: float
    product_url: HttpUrl
    missing_at_stores: list[str]


class BasketSingleStoreOption(BaseModel):
    store: str
    total_kes: float | None
    missing_items: list[str]


class BasketOptimizeResponse(BaseModel):
    is_demo_data: bool = True
    disclaimer: str | None = None
    data_label: str | None = None
    strategy: Literal["bfs", "ucs", "astar"]
    total_cost: float
    nodes_expanded: int
    assignments: list[BasketSearchAssignment]
    lines: list[BasketOptimizedLine] = Field(default_factory=list)
    best_single_store: str | None = None
    best_single_store_total: float | None = None
    best_single_store_missing: list[str] = Field(default_factory=list)
    single_store_options: list[BasketSingleStoreOption] = Field(default_factory=list)


class ListingImage(BaseModel):
    image_url: HttpUrl
    attribution: str
    source_page: HttpUrl
    licence_note: str


class ListingItem(BaseModel):
    id: str
    supermarket: str
    item_name: str
    price_kes: float
    regular_price_kes: float | None
    pack_size: str | None
    quantity: float | None
    unit: Literal["kg", "l", "pcs"] | None
    unit_price: float | None
    discount_pct: float | None
    category: str
    category_source: str
    grocery: bool
    product_url: HttpUrl
    listing_url: str
    location_context: str | None
    collected_at: str
    collection_method: str
    pack_size_source: str | None
    data_notes: str | None
    image: ListingImage | None = None


class ListingCollectionResponse(BaseModel):
    data_label: str
    caveats: str
    total: int
    limit: int
    offset: int
    items: list[ListingItem]


class ListingDetailResponse(BaseModel):
    data_label: str
    caveats: str
    item: ListingItem


class ListingDealPositionResponse(BaseModel):
    data_label: str
    listing_id: str
    group_id: str | None
    score: float | None
    label: Literal["low", "typical", "high"] | None
    reason: str
    discount_memberships: dict[str, float] | None
    price_memberships: dict[str, float] | None
    group_percentiles: dict[str, float] | None


class ListingGroup(BaseModel):
    group_id: str
    label: str
    basis: str
    stores: list[str]
    missing_at_stores: list[str]
    items: list[ListingItem]


class ListingGroupCollectionResponse(BaseModel):
    data_label: str
    caveats: str
    groups: list[ListingGroup]


class OrderLineRequest(BaseModel):
    listing_id: str = Field(min_length=1, max_length=80)
    quantity: int = Field(ge=1, le=20)


class OrderCreateRequest(BaseModel):
    store: str = Field(min_length=1, max_length=80)
    items: list[OrderLineRequest] = Field(min_length=1, max_length=30)
    delivery_address: str = Field(min_length=10, max_length=200)
    phone: str = Field(min_length=9, max_length=24)
    latitude: float | None = Field(default=None, ge=-90, le=90)
    longitude: float | None = Field(default=None, ge=-180, le=180)


class OrderResponse(BaseModel):
    id: str
    store: str
    lines: list[dict]
    subtotal: float
    delivery_address: str
    latitude: float | None
    longitude: float | None
    phone: str
    status: str
    created_at: str
    payment_reference: str | None
    merchant_request_id: str | None
    checkout_request_id: str | None
    delivery_fee: None
    delivery_fee_note: str
    prototype_disclaimer: str


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


class ToolSearchListingsArgs(BaseModel):
    q: str = Field(min_length=1, max_length=120)
    store: str | None
    grocery_only: bool
    max_price: float | None = Field(ge=0, allow_inf_nan=False)
    limit: int = Field(ge=1, le=10)
    model_config = ConfigDict(frozen=True, extra="forbid")

    @field_validator("q")
    @classmethod
    def clean_query(cls, value: str) -> str:
        query = value.strip()
        if not query:
            raise ValueError("q must not be blank")
        return query


class ToolGetListingArgs(BaseModel):
    id: str = Field(min_length=1, max_length=40)
    model_config = ConfigDict(frozen=True, extra="forbid")


class ToolCompareGroupArgs(BaseModel):
    group_id: str = Field(min_length=1, max_length=80)
    model_config = ConfigDict(frozen=True, extra="forbid")
