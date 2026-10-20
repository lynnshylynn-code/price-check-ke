"""Compare search effort for a small basket from the demo catalog."""

from price_check_api.basket_search import a_star_search, breadth_first_search, uniform_cost_search
from price_check_api.product_catalog import PRODUCT_CATALOG


def main() -> None:
    chosen = PRODUCT_CATALOG[:4]
    options = [
        {price.store: price.price for price in product.prices}
        for product in chosen
    ]
    print("Illustrative demo prices only")
    print(f"{'Algorithm':<24} {'Total':>10} {'Nodes expanded':>16}")
    for label, search in (
        ("Breadth-first", breadth_first_search),
        ("Uniform-cost", uniform_cost_search),
        ("A*", a_star_search),
    ):
        _assignment, cost, expanded = search(options)
        print(f"{label:<24} KES {cost:>6.2f} {expanded:>16}")


if __name__ == "__main__":
    main()
