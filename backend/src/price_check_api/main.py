import os
from datetime import date
from typing import Annotated, Literal

from fastapi import Depends, FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware

from .ai_insights import answer_market_question
from .ai_rate_limit import enforce_ai_rate_limit
from .market_data import (
    COMMODITIES,
    SOURCE_NAME,
    SOURCE_URL,
    get_food_inflation_response,
    get_market_directory,
    get_market_prices,
)
from .offline_answers import answer_question_offline
from .product_catalog import get_product_catalog, price_basket
from .schemas import (
    BasketPricingRequest,
    BasketPricingResponse,
    FoodInflationResponse,
    MarketDirectoryResponse,
    MarketQuestionRequest,
    MarketQuestionResponse,
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
