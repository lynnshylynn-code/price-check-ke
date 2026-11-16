import csv
from datetime import datetime
from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import ValidationError

from .schemas import (
    BasketLineRequest,
    BasketPricedLine,
    BasketPricingResponse,
    BasketStoreTotal,
    CatalogProduct,
    CatalogStorePrice,
    ProductCatalogResponse,
)

STORE_NAMES = ("Naivas", "Carrefour", "Jaza", "Quickmart")
DATA_FILE = (
    Path(__file__).resolve().parents[2]
    / "data"
    / "listings"
    / "nairobi_price_observations.csv"
)
DISCLAIMER = (
    "Public listing prices observed in Nairobi; not checkout totals or availability guarantees. "
    "Prices may change after observation."
)
UNVERIFIED_AREA_CAVEAT = (
    "No verified supermarket price observations are currently available for this area."
)


class ProductCatalogDataError(ValueError):
    pass


@lru_cache(maxsize=1)
def _load_products() -> tuple[CatalogProduct, ...]:
    try:
        with DATA_FILE.open(encoding="utf-8-sig", newline="") as source:
            reader = csv.DictReader(source)
            required_columns = {
                "product_id",
                "product_name",
                "size",
                "description",
                "category",
                "supermarket",
                "item_name",
                "price_kes",
                "regular_price_kes",
                "location_id",
                "location_name",
                "location_context",
                "product_url",
                "observed_at",
                "comparison_note",
            }
            required_values = required_columns - {"regular_price_kes", "comparison_note"}
            if not reader.fieldnames or not required_columns.issubset(reader.fieldnames):
                raise ProductCatalogDataError("Nairobi price data has an invalid header.")

            grouped: dict[str, dict[str, object]] = {}
            for row in reader:
                if None in row.values() or any(
                    not row.get(column, "").strip() for column in required_values
                ):
                    raise ProductCatalogDataError("Nairobi price data contains an incomplete row.")
                supermarket = row["supermarket"]
                if supermarket not in STORE_NAMES:
                    raise ProductCatalogDataError(
                        f"Unknown supermarket '{supermarket}' in Nairobi price data."
                    )

                try:
                    price = float(row["price_kes"])
                    regular_price = (
                        float(row["regular_price_kes"])
                        if row["regular_price_kes"].strip()
                        else None
                    )
                    observed_at = datetime.fromisoformat(row["observed_at"])
                    store_price = CatalogStorePrice(
                        store=supermarket,
                        location_id=row["location_id"],
                        location_name=row["location_name"],
                        location_context=row["location_context"],
                        item_name=row["item_name"],
                        price=price,
                        regular_price=regular_price,
                        product_url=row["product_url"],
                        observed_at=observed_at,
                    )
                except (TypeError, ValueError, ValidationError) as error:
                    raise ProductCatalogDataError(
                        "Nairobi price data contains an invalid price, timestamp, or URL."
                    ) from error
                if price <= 0 or (regular_price is not None and regular_price <= 0):
                    raise ProductCatalogDataError(
                        "Nairobi price data contains a non-positive price."
                    )

                product_id = row["product_id"]
                if product_id not in grouped:
                    grouped[product_id] = {
                        "name": row["product_name"],
                        "size": row["size"],
                        "description": row["description"],
                        "category": row["category"],
                        "comparison_note": row["comparison_note"] or None,
                        "prices": [],
                    }
                group = grouped[product_id]
                group["prices"].append(store_price)

            if not grouped:
                raise ProductCatalogDataError("Nairobi price data contains no observations.")

            products: list[CatalogProduct] = []
            for product_id, group in grouped.items():
                prices = group["prices"]
                if not isinstance(prices, list):
                    raise ProductCatalogDataError(
                        "Nairobi price data has invalid product grouping."
                    )
                available_stores = {price.store for price in prices}
                products.append(
                    CatalogProduct(
                        id=product_id,
                        name=group["name"],
                        size=group["size"],
                        description=group["description"],
                        category=group["category"],
                        comparison_note=group["comparison_note"],
                        missing_at_stores=sorted(set(STORE_NAMES) - available_stores),
                        prices=sorted(prices, key=lambda price: (price.store, price.location_name)),
                    )
                )
    except ProductCatalogDataError:
        raise
    except (OSError, csv.Error, UnicodeDecodeError) as error:
        raise ProductCatalogDataError("Nairobi price data could not be read.") from error

    return tuple(sorted(products, key=lambda product: (product.category, product.name)))


def get_product_catalog(area: str = "Nairobi") -> ProductCatalogResponse:
    if area.strip().casefold() != "nairobi":
        return ProductCatalogResponse(
            area=area.strip(),
            data_label=f"No verified retailer listings for {area.strip()}",
            caveats=UNVERIFIED_AREA_CAVEAT,
            products=[],
        )

    products = _load_products()
    latest_observation = max(
        price.observed_at for product in products for price in product.prices
    )
    return ProductCatalogResponse(
        area="Nairobi",
        data_label=f"Public retailer listings observed through {latest_observation:%d %b %Y}",
        caveats=(
            "Coverage is limited to the exact location contexts shown on each listing: "
            "Naivas Nairobi delivery (serving branch not identified), Quickmart Kilimani, "
            "and Quickmart bicycle search results with Westlands selected (only one seller was "
            "independently confirmed as Quickmart Westlands). No current Nairobi prices were "
            "verified for Carrefour or Jaza, and this is not a complete retailer catalog. "
            "The sugar comparison is between different brands in the same pack size. "
            "An absent retailer is unknown, not evidence that the item is unavailable."
        ),
        products=list(products),
    )


def _location_prices(product: CatalogProduct) -> dict[str, CatalogStorePrice]:
    locations: dict[str, CatalogStorePrice] = {}
    for price in product.prices:
        current = locations.get(price.location_id)
        if current is None or price.price < current.price:
            locations[price.location_id] = price
    return locations


def _location_label(price: CatalogStorePrice) -> str:
    return f"{price.store} - {price.location_name}"


def price_basket(
    items: list[BasketLineRequest],
    strategy: Literal["lowest", "single"],
    area: str = "Nairobi",
) -> BasketPricingResponse:
    if area.strip().casefold() != "nairobi":
        raise ValueError(f"No verified supermarket price observations are available for {area}.")

    products_by_id = {product.id: product for product in _load_products()}
    products = []
    seen_ids: set[str] = set()
    for item in items:
        if item.product_id in seen_ids:
            raise ValueError(f"Duplicate product id '{item.product_id}'.")
        product = products_by_id.get(item.product_id)
        if product is None:
            raise KeyError(f"Unknown product id '{item.product_id}'.")
        seen_ids.add(item.product_id)
        products.append((item, product, _location_prices(product)))

    available_locations: set[str] | None = None
    for _item, _product, prices_by_location in products:
        locations = set(prices_by_location)
        available_locations = (
            locations
            if available_locations is None
            else available_locations & locations
        )
    eligible_locations = available_locations or set()

    location_metadata = {
        price.location_id: price
        for _item, _product, prices_by_location in products
        for price in prices_by_location.values()
    }
    comparison = sorted(
        (
            BasketStoreTotal(
                store=_location_label(location_metadata[location_id]),
                location_id=location_id,
                total=round(
                    sum(
                        prices_by_location[location_id].price * item.quantity
                        for item, _product, prices_by_location in products
                    ),
                    2,
                ),
            )
            for location_id in eligible_locations
        ),
        key=lambda item: (item.total, item.store),
    )
    best_single_store = comparison[0].store if comparison else None
    best_single_location_id = comparison[0].location_id if comparison else None

    lines: list[BasketPricedLine] = []
    for item, product, prices_by_location in products:
        if strategy == "single":
            if best_single_location_id is None:
                raise ValueError("No single verified location has prices for every basket item.")
            selected = prices_by_location[best_single_location_id]
        else:
            selected = min(
                prices_by_location.values(),
                key=lambda price: (price.price, price.store),
            )
        lines.append(
            BasketPricedLine(
                product_id=product.id,
                product_name=product.name,
                quantity=item.quantity,
                store=_location_label(selected),
                location_id=selected.location_id,
                unit_price=selected.price,
                total=round(selected.price * item.quantity, 2),
            )
        )

    return BasketPricingResponse(
        disclaimer=DISCLAIMER,
        strategy=strategy,
        best_single_store=best_single_store,
        best_single_location_id=best_single_location_id,
        store_totals=comparison,
        total=round(sum(line.total for line in lines), 2),
        lines=lines,
    )
