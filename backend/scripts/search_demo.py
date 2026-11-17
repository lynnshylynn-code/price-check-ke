"""Compare search effort for a small basket from the demo catalog."""

from price_check_api.basket_search import (
    a_star_search,
    breadth_first_search,
    depth_first_search,
    greedy_best_first_search,
    iterative_deepening_search,
    uniform_cost_search,
)
from price_check_api.local_search import (
    hill_climbing,
    pricing_game_alpha_beta,
    pricing_game_minimax,
    simulated_annealing,
)
from price_check_api.product_catalog import get_product_catalog


def main() -> None:
    catalog = get_product_catalog()
    chosen = catalog.products[:4]
    options = []
    for product in chosen:
        by_store = {}
        for price in product.prices:
            if price.store not in by_store or price.price < by_store[price.store]:
                by_store[price.store] = price.price
        options.append(by_store)
    print(catalog.data_label)
    print(catalog.caveats)
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
    initial = tuple(min(item, key=item.get) for item in options)
    hill = hill_climbing(options, initial_assignment=initial, trip_cost=0, seed=42)
    annealed = simulated_annealing(options, initial_assignment=initial, seed=42)
    results.extend(
        [
            ("Hill climbing + restarts", hill.cost, hill.steps),
            ("Simulated annealing", annealed.cost, annealed.steps),
        ]
    )
    optimal_cost = next(cost for label, cost, _ in results if label == "Uniform-cost")
    print(f"{'Algorithm':<24} {'Total (KES)':>12} {'Optimal here?':>15} {'Nodes':>8}")
    for label, cost, expanded in results:
        optimal = "Yes" if cost == optimal_cost else "No"
        print(f"{label:<24} {cost:>12.2f} {optimal:>15} {expanded:>8}")
    plain = pricing_game_minimax()
    pruned = pricing_game_alpha_beta()
    print("\nIllustrative pricing game teaching demo (arbitrary payoffs; not a market model)")
    print(
        f"Minimax value/action/nodes: {plain.value}/{plain.action}/{plain.nodes_expanded}; "
        f"alpha-beta: {pruned.value}/{pruned.action}/{pruned.nodes_expanded}"
    )


if __name__ == "__main__":
    main()
