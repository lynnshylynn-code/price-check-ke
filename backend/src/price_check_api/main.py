import logging
import os
import re
from datetime import date
from typing import Annotated, Literal

from fastapi import Depends, FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware

from . import orders
from .ai_insights import answer_market_question
from .ai_rate_limit import enforce_ai_rate_limit
from .basket_search import a_star_search, breadth_first_search, uniform_cost_search
from .fuzzy_listings import deal_position as listing_deal_position
from .fuzzy_price import price_position
from .listing_groups import get_comparable_group, get_comparable_groups
from .listings import DATA_CAVEATS, DATA_LABEL, ListingDataError, get_listings, listing_dict
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
    BasketOptimizedLine,
    BasketOptimizeRequest,
    BasketOptimizeResponse,
    BasketPricingRequest,
    BasketPricingResponse,
    BasketSearchAssignment,
    BasketSingleStoreOption,
    FoodInflationResponse,
    ListingCollectionResponse,
    ListingDealPositionResponse,
    ListingDetailResponse,
    ListingGroup,
    ListingGroupCollectionResponse,
    MarketDirectoryResponse,
    MarketQuestionRequest,
    MarketQuestionResponse,
    OrderCreateRequest,
    OrderResponse,
    PricePositionResponse,
    PriceSeriesResponse,
    ProductCatalogResponse,
)

app = FastAPI(
    title="Price Check KE API",
    description="Kenya food-market data, summaries, and source-grounded AI exploration.",
    version="0.1.0",
)


class CallbackSecretLogFilter(logging.Filter):
    """Redact the callback token from the standard Uvicorn access log record."""

    def filter(self, record: logging.LogRecord) -> bool:
        secret = os.getenv("PRICE_CHECK_CALLBACK_SECRET")
        if secret and isinstance(record.args, tuple):
            record.args = tuple(
                re.sub(re.escape(secret), "[redacted]", value)
                if isinstance(value, str)
                else value
                for value in record.args
            )
        return True


logging.getLogger("uvicorn.access").addFilter(CallbackSecretLogFilter())

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


def _listing_collection(requested: list, limit: int, offset: int) -> ListingCollectionResponse:
    return ListingCollectionResponse(
        data_label=DATA_LABEL,
        caveats=DATA_CAVEATS,
        total=len(requested),
        limit=limit,
        offset=offset,
        items=[listing_dict(item) for item in requested[offset:offset + limit]],
    )


@app.get("/api/v1/listings", response_model=ListingCollectionResponse, tags=["listings"])
def listings(
    store: Annotated[str | None, Query(min_length=1, max_length=40)] = None,
    q: Annotated[str | None, Query(min_length=1, max_length=120)] = None,
    category: Annotated[str | None, Query(min_length=1, max_length=40)] = None,
    max_price: Annotated[float | None, Query(gt=0)] = None,
    grocery_only: bool = False,
    limit: Annotated[int, Query(ge=1, le=100)] = 30,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> ListingCollectionResponse:
    try:
        filtered = list(get_listings())
    except ListingDataError as error:
        raise HTTPException(status_code=503, detail="Listing snapshot is unavailable.") from error
    if store:
        filtered = [item for item in filtered if item.supermarket.casefold() == store.casefold()]
    if q:
        query = q.casefold()
        filtered = [item for item in filtered if query in item.item_name.casefold()]
    if category:
        filtered = [item for item in filtered if item.category.casefold() == category.casefold()]
    if max_price is not None:
        filtered = [item for item in filtered if item.price_kes <= max_price]
    if grocery_only:
        filtered = [item for item in filtered if item.grocery]
    filtered.sort(key=lambda item: (item.supermarket.casefold(), item.item_name.casefold()))
    return _listing_collection(filtered, limit, offset)


@app.get(
    "/api/v1/listings/{listing_id}", response_model=ListingDetailResponse, tags=["listings"]
)
def listing_detail(listing_id: str) -> ListingDetailResponse:
    try:
        item = next((row for row in get_listings() if row.id == listing_id), None)
    except ListingDataError as error:
        raise HTTPException(status_code=503, detail="Listing snapshot is unavailable.") from error
    if item is None:
        raise HTTPException(status_code=404, detail="Listing not found in this snapshot.")
    return ListingDetailResponse(
        data_label=DATA_LABEL, caveats=DATA_CAVEATS, item=listing_dict(item)
    )


@app.get(
    "/api/v1/listings/{listing_id}/deal-position",
    response_model=ListingDealPositionResponse,
    tags=["listings"],
)
def listing_deal_position_endpoint(listing_id: str) -> ListingDealPositionResponse:
    try:
        item = next((row for row in get_listings() if row.id == listing_id), None)
    except ListingDataError as error:
        raise HTTPException(status_code=503, detail="Listing snapshot is unavailable.") from error
    if item is None:
        raise HTTPException(status_code=404, detail="Listing not found in this snapshot.")
    group = next(
        (candidate for candidate in get_comparable_groups()
         if any(row.id == item.id for row in candidate.listings)),
        None,
    )
    peers = (
        [row.unit_price for row in group.listings if row.unit_price is not None]
        if group
        else []
    )
    result = listing_deal_position(item.discount_pct, item.unit_price, peers)
    return ListingDealPositionResponse(
        data_label=DATA_LABEL,
        listing_id=item.id,
        group_id=group.id if group else None,
        score=result.score,
        label=result.label,
        reason=result.reason,
        discount_memberships=result.discount_memberships,
        price_memberships=result.price_memberships,
        group_percentiles=result.group_percentiles,
    )


@app.get(
    "/api/v1/listing-groups",
    response_model=ListingGroupCollectionResponse,
    tags=["listings"],
)
def listing_groups() -> ListingGroupCollectionResponse:
    groups = get_comparable_groups()
    stores = sorted({item.supermarket for item in get_listings()})
    return ListingGroupCollectionResponse(
        data_label=DATA_LABEL,
        caveats=DATA_CAVEATS,
        groups=[
            ListingGroup(
                group_id=group.id,
                label=group.label,
                basis=group.basis,
                stores=sorted({item.supermarket for item in group.listings}),
                missing_at_stores=sorted(
                    set(stores) - {item.supermarket for item in group.listings}
                ),
                items=[listing_dict(item) for item in group.listings],
            )
            for group in groups
        ],
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
    if request.group_ids:
        groups = [get_comparable_group(group_id) for group_id in request.group_ids]
        if any(group is None for group in groups):
            raise HTTPException(status_code=404, detail="Comparable listing group not found.")
        selected_groups = [group for group in groups if group is not None]
        quantities = request.quantities or [1] * len(selected_groups)
        stores = sorted({item.supermarket for item in get_listings()})
        options = [
            {
                item.supermarket: item.price_kes * quantity
                for item in group.listings
            }
            for group, quantity in zip(selected_groups, quantities, strict=True)
        ]
        search = {
            "bfs": breadth_first_search,
            "ucs": uniform_cost_search,
            "astar": a_star_search,
        }[request.strategy]
        try:
            assignment, cost, nodes = search(options, trip_cost=request.trip_cost)
        except ValueError as error:
            raise HTTPException(status_code=422, detail=str(error)) from error
        chosen_lines = []
        for group, quantity, store in zip(
            selected_groups, quantities, assignment, strict=True
        ):
            item = next(row for row in group.listings if row.supermarket == store)
            chosen_lines.append(BasketOptimizedLine(
                group_id=group.id,
                item_name=item.item_name,
                listing_id=item.id,
                store=store,
                quantity=quantity,
                price_kes=item.price_kes,
                unit_price=item.unit_price,
                line_total_kes=item.price_kes * quantity,
                product_url=item.product_url,
                missing_at_stores=sorted(
                    set(stores) - {row.supermarket for row in group.listings}
                ),
            ))
        single_store_options = []
        for store in stores:
            missing = [
                group.label for group in selected_groups
                if not any(item.supermarket == store for item in group.listings)
            ]
            total = None if missing else sum(
                next(item.price_kes for item in group.listings if item.supermarket == store)
                * quantity
                for group, quantity in zip(selected_groups, quantities, strict=True)
            )
            single_store_options.append(BasketSingleStoreOption(
                store=store, total_kes=total, missing_items=missing
            ))
        complete_stores = [
            option for option in single_store_options if option.total_kes is not None
        ]
        best_single = min(complete_stores, key=lambda option: option.total_kes or 0, default=None)
        return BasketOptimizeResponse(
            is_demo_data=False,
            data_label=DATA_LABEL,
            strategy=request.strategy,
            total_cost=cost,
            nodes_expanded=nodes,
            assignments=[
                BasketSearchAssignment(product_id=line.listing_id, store=line.store)
                for line in chosen_lines
            ],
            lines=chosen_lines,
            best_single_store=best_single.store if best_single else None,
            best_single_store_total=best_single.total_kes if best_single else None,
            best_single_store_missing=best_single.missing_items if best_single else [],
            single_store_options=single_store_options,
        )

    products_by_id = {product.id: product for product in PRODUCT_CATALOG}
    product_ids = request.product_ids or []
    unknown = [product_id for product_id in product_ids if product_id not in products_by_id]
    if unknown:
        raise HTTPException(status_code=404, detail=f"Unknown product id: {unknown[0]}")
    selected = [products_by_id[product_id] for product_id in product_ids]
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


@app.post("/api/v1/orders", response_model=OrderResponse, tags=["prototype orders"])
def order_create(request: OrderCreateRequest) -> OrderResponse:
    try:
        return orders.create_order(request.model_dump())
    except ValueError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error


@app.get("/api/v1/orders/{order_id}", response_model=OrderResponse, tags=["prototype orders"])
def order_status(order_id: str) -> OrderResponse:
    result = orders.get_order(order_id)
    if result is None:
        raise HTTPException(status_code=404, detail="Order not found.")
    return result


@app.post(
    "/api/v1/orders/{order_id}/cancel",
    response_model=OrderResponse,
    tags=["prototype orders"],
)
def order_cancel(order_id: str) -> OrderResponse:
    try:
        result = orders.update_order(order_id, "cancelled")
    except ValueError as error:
        raise HTTPException(status_code=409, detail=str(error)) from error
    if result is None:
        raise HTTPException(status_code=404, detail="Order not found.")
    return result


@app.delete("/api/v1/orders/{order_id}", tags=["prototype orders"])
def order_delete(order_id: str) -> dict[str, bool]:
    if not orders.delete_order(order_id):
        raise HTTPException(status_code=404, detail="Order not found.")
    return {"deleted": True}


@app.post("/api/v1/orders/{order_id}/pay", response_model=OrderResponse, tags=["prototype orders"])
def order_pay(order_id: str) -> OrderResponse:
    current = orders.get_order(order_id)
    if current is None:
        raise HTTPException(status_code=404, detail="Order not found.")
    if current["status"] not in {"created", "failed"}:
        raise HTTPException(
            status_code=409,
            detail=f"Order cannot be paid while it is {current['status']}.",
        )
    try:
        provider = (
            orders.DarajaSandboxProvider()
            if os.getenv("PRICE_CHECK_PAYMENTS") == "daraja_sandbox"
            else orders.MockPaymentProvider()
        )
        status, reference = provider.pay(order_id)
        if isinstance(provider, orders.DarajaSandboxProvider):
            # The provider atomically persisted both Daraja request identifiers.
            return orders.get_order(order_id)  # type: ignore[return-value]
        if status == "paid_sandbox" and current["status"] == "failed":
            orders.update_order(order_id, "payment_pending")
        result = orders.update_order(order_id, status, reference)
        return result  # type: ignore[return-value]
    except LookupError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error
    except ValueError as error:
        raise HTTPException(status_code=409, detail=str(error)) from error
    except RuntimeError as error:
        raise HTTPException(status_code=503, detail=str(error)) from error


@app.post("/api/v1/payments/mpesa/callback/{secret}", tags=["prototype orders"])
def mpesa_callback(secret: str, payload: dict) -> dict[str, str]:
    expected = os.getenv("PRICE_CHECK_CALLBACK_SECRET")
    if not orders.callback_secret_matches(secret, expected):
        raise HTTPException(status_code=403, detail="Invalid callback token.")
    callback = payload.get("Body", {}).get("stkCallback", {})
    checkout_id = callback.get("CheckoutRequestID")
    result_code = callback.get("ResultCode")
    if not checkout_id or result_code is None:
        raise HTTPException(status_code=422, detail="Invalid Daraja callback payload.")
    metadata = callback.get("CallbackMetadata", {}).get("Item", [])
    values = {row.get("Name"): row.get("Value") for row in metadata if isinstance(row, dict)}
    try:
        outcome, order = orders.apply_mpesa_callback(
            str(checkout_id), int(result_code), values.get("Amount"),
            str(values["MpesaReceiptNumber"]) if values.get("MpesaReceiptNumber") else None,
        )
    except LookupError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error
    except ValueError as error:
        raise HTTPException(status_code=409, detail=str(error)) from error
    return {"result": outcome, "order_id": order["id"] if order else ""}
