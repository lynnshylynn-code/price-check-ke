import os
from datetime import date
from typing import Annotated, Literal

from fastapi import Depends, FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware

from .ai_insights import answer_market_question
from .ai_rate_limit import enforce_ai_rate_limit
from .basket_search import a_star_search, breadth_first_search, uniform_cost_search
from .fuzzy_price import price_position
from .market_data import (
    COMMODITIES,
    SOURCE_NAME,
    SOURCE_URL,
    get_food_inflation_response,
    get_market_directory,
    get_market_prices,
)
from .offline_answers import answer_question_offline
from .product_catalog import PRODUCT_CATALOG, get_product_catalog, price_basket
from .schemas import (
    BasketOptimizeRequest,
    BasketOptimizeResponse,
    BasketPricingRequest,
    BasketPricingResponse,
    BasketSearchAssignment,
    FoodInflationResponse,
    MarketDirectoryResponse,
    MarketQuestionRequest,
    MarketQuestionResponse,
    PricePositionResponse,
    PriceSeriesResponse,
    ProductCatalogResponse,
)

app = FastAPI(
    title="Price Check KE API",
    description="Kenya food-market data, summaries, and source-grounded AI exploration.",
    version="0.1.0",
)

default_origins = (
    "http://localhost:8081,http://localhost:8082,http://localhost:8083,http://localhost:8084,"
    "http://127.0.0.1:8081,http://127.0.0.1:8082,http://127.0.0.1:8083,http://127.0.0.1:8084"
)
allowed_origins = [
    origin.strip()
    for origin in os.getenv("PRICE_CHECK_CORS_ORIGINS", default_origins).split(",")
    if origin.strip()
]
app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)


@app.get("/health", tags=["health"])
def health_check() -> dict[str, str]:
    return {"status": "ok"}


@app.get(
    "/api/v1/market/food-inflation",
    response_model=FoodInflationResponse,
    tags=["market data"],
)
def food_inflation() -> FoodInflationResponse:
    return get_food_inflation_response()


@app.get("/api/markets", response_model=MarketDirectoryResponse, tags=["market data"])
def markets() -> MarketDirectoryResponse:
    counties, market_options = get_market_directory()
    return MarketDirectoryResponse(
        source_name=SOURCE_NAME,
        source_url=SOURCE_URL,
        commodities=list(COMMODITIES.values()),
        counties=counties,
        markets=market_options,
    )


@app.get("/api/prices", response_model=PriceSeriesResponse, tags=["market data"])
def prices(
    market: Annotated[str, Query(min_length=1, max_length=120)],
    commodity: Annotated[Literal["beans", "maize", "goat"], Query()],
    from_date: Annotated[date | None, Query(alias="from")] = None,
    to_date: Annotated[date | None, Query(alias="to")] = None,
) -> PriceSeriesResponse:
    if from_date and to_date and to_date < from_date:
        raise HTTPException(status_code=422, detail="'to' must be on or after 'from'.")
    try:
        return get_market_prices(market, commodity, from_date, to_date)
    except KeyError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error
    except OverflowError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error


@app.get(
    "/api/v1/market/price-position",
    response_model=PricePositionResponse,
    tags=["market data"],
)
def market_price_position(
    market: Annotated[str, Query(min_length=1, max_length=120)],
    commodity: Annotated[Literal["beans", "maize", "goat"], Query()],
) -> PricePositionResponse:
    try:
        series = get_market_prices(market, commodity)
    except KeyError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error
    monthly: dict[date, list[float]] = {}
    for observation in series.observations:
        monthly.setdefault(observation.date, []).append(observation.price)
    monthly_means = [
        (month, sum(values) / len(values)) for month, values in sorted(monthly.items())
    ]
    history = [value for _, value in monthly_means]
    trend = None
    if len(history) >= 2:
        change = (history[-1] - history[-2]) / history[-2] if history[-2] else 0.0
        trend = "rising" if change > .02 else "falling" if change < -.02 else "stable"
    latest_date, latest_price = monthly_means[-1] if monthly_means else (None, None)
    position = (
        price_position(history[:-1], latest_price, trend)
        if latest_price is not None
        else price_position([], 0)
    )
    return PricePositionResponse(
        market=market,
        commodity=commodity,
        source_name=series.source_name,
        source_url=series.source_url,
        coverage_start=series.coverage_start,
        coverage_end=series.coverage_end,
        aggregation="monthly mean across observed source-market prices",
        latest_date=latest_date,
        latest_price=latest_price,
        recent_trend=trend,
        score=position.score,
        label=position.label,
        reason=position.reason,
        p10=position.p10,
        p50=position.p50,
        p90=position.p90,
        memberships=position.memberships,
    )


@app.get("/api/v1/products", response_model=ProductCatalogResponse, tags=["products"])
def products() -> ProductCatalogResponse:
    return get_product_catalog()


@app.post(
    "/api/v1/basket/pricing",
    response_model=BasketPricingResponse,
    tags=["products"],
)
def basket_pricing(request: BasketPricingRequest) -> BasketPricingResponse:
    try:
        return price_basket(request.items, request.strategy)
    except KeyError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error
    except ValueError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error


@app.post(
    "/api/v1/basket/optimize",
    response_model=BasketOptimizeResponse,
    tags=["products"],
)
def basket_optimize(request: BasketOptimizeRequest) -> BasketOptimizeResponse:
    products_by_id = {product.id: product for product in PRODUCT_CATALOG}
    unknown = [product_id for product_id in request.product_ids if product_id not in products_by_id]
    if unknown:
        raise HTTPException(status_code=404, detail=f"Unknown product id: {unknown[0]}")
    selected = [products_by_id[product_id] for product_id in request.product_ids]
    options = [{price.store: price.price for price in product.prices} for product in selected]
    algorithm = {
        "bfs": breadth_first_search,
        "ucs": uniform_cost_search,
        "astar": a_star_search,
    }[request.strategy]
    assignment, cost, nodes = algorithm(options, trip_cost=request.trip_cost)
    return BasketOptimizeResponse(
        disclaimer="Demo supermarket prices only; not live retailer data.",
        strategy=request.strategy,
        total_cost=cost,
        nodes_expanded=nodes,
        assignments=[
            BasketSearchAssignment(product_id=product.id, store=store)
            for product, store in zip(selected, assignment, strict=True)
        ],
    )


@app.post(
    "/api/v1/ai/market-question",
    response_model=MarketQuestionResponse,
    tags=["AI"],
    dependencies=[Depends(enforce_ai_rate_limit)],
)
async def market_question(request: MarketQuestionRequest) -> MarketQuestionResponse:
    return await answer_market_question(request.question)


@app.post(
    "/api/v1/ai/market-question/simulate",
    response_model=MarketQuestionResponse,
    tags=["AI"],
)
def simulate_market_question(request: MarketQuestionRequest) -> MarketQuestionResponse:
    return answer_question_offline(request.question)
