from typing import Literal

from .schemas import (
    BasketLineRequest,
    BasketPricedLine,
    BasketPricingResponse,
    BasketStoreTotal,
    DemoProduct,
    DemoStorePrice,
    ProductCatalogResponse,
)

DISCLAIMER = "Illustrative supermarket demo only; these are not verified or live retailer prices."
SOURCE_NOTE = "Catalog prices are synthetic examples and must never be represented as market data."

_PRODUCTS = (
    ("bread", "Supa Loaf Bread", "400g", "White sandwich loaf", "Bakery",
     (("Naivas", 65, "In stock"), ("Carrefour", 69, "In stock"),
      ("Jaza", 70, "In stock"), ("Quickmart", 72, "In stock"))),
    ("yoghurt", "KCC Yoghurt", "500ml", "Natural probiotic yoghurt", "Dairy",
     (("Jaza", 110, "In stock"), ("Naivas", 115, "In stock"),
      ("Carrefour", 119, "In stock"))),
    ("brookside-milk", "Brookside Milk", "1L", "Long life full cream", "Dairy",
     (("Carrefour", 139, "In stock"), ("Naivas", 145, "Low stock"),
      ("Jaza", 147, "In stock"), ("Quickmart", 150, "In stock"))),
    ("fresha-milk", "Fresha Milk", "1L", "Fresh whole milk", "Dairy",
     (("Naivas", 145, "In stock"), ("Jaza", 149, "In stock"),
      ("Quickmart", 152, "In stock"))),
    ("cooking-oil", "Fresh Fri Cooking Oil", "1L", "Pure vegetable oil", "Pantry",
     (("Carrefour", 245, "In stock"), ("Naivas", 252, "In stock"),
      ("Jaza", 256, "In stock"), ("Quickmart", 259, "In stock"))),
    ("sugar", "Kabras Sugar", "2kg", "Fine white sugar", "Pantry",
     (("Quickmart", 280, "In stock"), ("Naivas", 289, "In stock"),
      ("Jaza", 292, "In stock"), ("Carrefour", 295, "In stock"))),
    ("tomatoes", "Fresh Tomatoes", "1kg", "Fresh market tomatoes", "Produce",
     (("Naivas", 120, "In stock"), ("Carrefour", 135, "In stock"),
      ("Jaza", 125, "In stock"), ("Quickmart", 130, "In stock"))),
    ("onions", "Red Onions", "1kg", "Fresh red onions", "Produce",
     (("Naivas", 150, "In stock"), ("Carrefour", 160, "In stock"),
      ("Jaza", 145, "In stock"), ("Quickmart", 155, "In stock"))),
    ("maize-flour", "Soko Maize Flour", "2kg", "Fortified sifted maize flour", "Pantry",
     (("Naivas", 165, "In stock"), ("Carrefour", 172, "In stock"),
      ("Jaza", 168, "In stock"), ("Quickmart", 170, "In stock"))),
    ("eggs", "Farm Fresh Eggs", "Tray of 15", "Medium-size eggs", "Dairy",
     (("Naivas", 330, "In stock"), ("Carrefour", 345, "In stock"),
      ("Jaza", 325, "In stock"), ("Quickmart", 335, "In stock"))),
)

PRODUCT_CATALOG = tuple(
    DemoProduct(
        id=product_id,
        name=name,
        size=size,
        description=description,
        category=category,
        prices=[
            DemoStorePrice(store=store, price=price, stock=stock)
            for store, price, stock in prices
        ],
    )
    for product_id, name, size, description, category, prices in _PRODUCTS
)
_PRODUCT_BY_ID = {product.id: product for product in PRODUCT_CATALOG}


def get_product_catalog() -> ProductCatalogResponse:
    return ProductCatalogResponse(disclaimer=DISCLAIMER, products=list(PRODUCT_CATALOG))


def price_basket(
    items: list[BasketLineRequest],
    strategy: Literal["lowest", "single"],
) -> BasketPricingResponse:
    products = []
    seen_ids: set[str] = set()
    for item in items:
        if item.product_id in seen_ids:
            raise ValueError(f"Duplicate product id '{item.product_id}'.")
        product = _PRODUCT_BY_ID.get(item.product_id)
        if product is None:
            raise KeyError(f"Unknown product id '{item.product_id}'.")
        seen_ids.add(item.product_id)
        products.append((item, product))

    store_totals: dict[str, float] = {}
    available_stores: set[str] | None = None
    for item, product in products:
        prices = {price.store: price.price for price in product.prices}
        available_stores = (
            set(prices) if available_stores is None else available_stores & prices.keys()
        )
        for store in prices:
            store_totals[store] = store_totals.get(store, 0.0) + prices[store] * item.quantity

    eligible_stores = available_stores or set()
    comparison = sorted(
        (
            BasketStoreTotal(store=store, total=round(store_totals[store], 2))
            for store in eligible_stores
        ),
        key=lambda item: (item.total, item.store),
    )
    best_single_store = comparison[0].store if comparison else None
    if strategy == "single" and best_single_store is None:
        raise ValueError("No single store has demo prices for every basket item.")

    lines: list[BasketPricedLine] = []
    for item, product in products:
        if strategy == "single":
            selected = next(price for price in product.prices if price.store == best_single_store)
        else:
            selected = min(product.prices, key=lambda price: (price.price, price.store))
        lines.append(
            BasketPricedLine(
                product_id=product.id,
                product_name=product.name,
                quantity=item.quantity,
                store=selected.store,
                unit_price=selected.price,
                total=round(selected.price * item.quantity, 2),
            )
        )

    total = round(sum(line.total for line in lines), 2)
    return BasketPricingResponse(
        disclaimer=DISCLAIMER,
        strategy=strategy,
        best_single_store=best_single_store,
        store_totals=comparison,
        total=total,
        lines=lines,
    )
