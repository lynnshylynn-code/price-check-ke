"""Compare search effort for a small basket from the demo catalog."""

from price_check_api.basket_search import (
    a_star_search,
    breadth_first_search,
    depth_first_search,
    greedy_best_first_search,
    iterative_deepening_search,
    uniform_cost_search,
)
from price_check_api.product_catalog import PRODUCT_CATALOG


def main() -> None:
    chosen = PRODUCT_CATALOG[:4]
    options = [
        {price.store: price.price for price in product.prices}
        for product in chosen
    ]
    print("Illustrative demo prices only")
    results = []
    for label, search in (
        ("Breadth-first", breadth_first_search),
        ("Depth-first", depth_first_search),
        ("Uniform-cost", uniform_cost_search),
        ("Iterative deepening", iterative_deepening_search),
        ("Greedy best-first", greedy_best_first_search),
        ("A*", a_star_search),
    ):
        _assignment, cost, expanded = search(options)
        results.append((label, cost, expanded))
    optimal_cost = next(cost for label, cost, _ in results if label == "Uniform-cost")
    print(f"{'Algorithm':<24} {'Total (KES)':>12} {'Optimal here?':>15} {'Nodes':>8}")
    for label, cost, expanded in results:
        optimal = "Yes" if cost == optimal_cost else "No"
        print(f"{label:<24} {cost:>12.2f} {optimal:>15} {expanded:>8}")


if __name__ == "__main__":
    main()
