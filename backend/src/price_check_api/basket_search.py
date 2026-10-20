"""Search algorithms for the illustrative supermarket demo basket.

State: (index of the next item, store choices made so far). Actions choose an
available store for the next item; the goal is to assign every item. The initial
state is (0, ()). The finite state space is the product of each item's store set.
Prices and optional fixed visit costs are demo inputs, not live prices.
"""

from __future__ import annotations

import heapq
from collections import deque
from collections.abc import Mapping, Sequence

PriceOptions = Sequence[Mapping[str, float]]
Assignment = tuple[str, ...]


def _search(
    prices: PriceOptions,
    strategy: str,
    trip_cost: float,
) -> tuple[Assignment, float, int]:
    if trip_cost < 0:
        raise ValueError("trip_cost must be non-negative")
    if not prices:
        return (), 0.0, 0
    if any(not item for item in prices):
        raise ValueError("each item must have at least one store price")

    def path_cost(choices: Assignment) -> float:
        selected = sum(prices[i][store] for i, store in enumerate(choices))
        visits = len(set(choices))
        return selected + trip_cost * max(0, visits - 1)

    def heuristic(index: int) -> float:
        # Admissible: this sums each remaining item's minimum item price and
        # ignores any non-negative future trip cost, so it can never overestimate.
        return sum(min(item.values()) for item in prices[index:])

    start: Assignment = ()
    expanded = 0
    if strategy == "bfs":
        frontier = deque([start])
        while frontier:
            choices = frontier.popleft()
            expanded += 1
            index = len(choices)
            if index == len(prices):
                return choices, path_cost(choices), expanded
            else:
                for store in sorted(prices[index]):
                    frontier.append((*choices, store))
    elif strategy in {"ucs", "astar"}:
        frontier: list[tuple[float, int, Assignment]] = []
        serial = 0
        heapq.heappush(frontier, (heuristic(0) if strategy == "astar" else 0, serial, start))
        best_cost: dict[Assignment, float] = {start: 0.0}
        while frontier:
            _, _, choices = heapq.heappop(frontier)
            current_cost = path_cost(choices)
            if current_cost > best_cost.get(choices, float("inf")):
                continue
            expanded += 1
            index = len(choices)
            if index == len(prices):
                return choices, current_cost, expanded
            for store in sorted(prices[index]):
                child = (*choices, store)
                cost = path_cost(child)
                if cost >= best_cost.get(child, float("inf")):
                    continue
                best_cost[child] = cost
                serial += 1
                estimate = cost + (heuristic(index + 1) if strategy == "astar" else 0)
                heapq.heappush(frontier, (estimate, serial, child))
    elif strategy == "greedy":
        frontier = [(heuristic(0), 0, start)]
        serial = 0
        while frontier:
            _, _, choices = heapq.heappop(frontier)
            expanded += 1
            index = len(choices)
            if index == len(prices):
                return choices, path_cost(choices), expanded
            for store in sorted(prices[index]):
                serial += 1
                heapq.heappush(frontier, (heuristic(index + 1), serial, (*choices, store)))
    elif strategy == "dfs":
        frontier = [start]
        while frontier:
            choices = frontier.pop()
            expanded += 1
            index = len(choices)
            if index == len(prices):
                return choices, path_cost(choices), expanded
            for store in reversed(sorted(prices[index])):
                frontier.append((*choices, store))
    elif strategy == "iddfs":
        def depth_limited(limit: int) -> tuple[Assignment, float, int] | None:
            nonlocal expanded
            stack = [start]
            while stack:
                choices = stack.pop()
                expanded += 1
                if len(choices) == len(prices):
                    return choices, path_cost(choices), expanded
                if len(choices) < limit:
                    for store in reversed(sorted(prices[len(choices)])):
                        stack.append((*choices, store))
            return None

        for depth in range(len(prices) + 1):
            result = depth_limited(depth)
            if result is not None:
                return result
    else:
        raise ValueError(f"unknown search strategy: {strategy}")
    raise RuntimeError("search frontier exhausted")


def breadth_first_search(
    prices: PriceOptions, trip_cost: float = 0.0
) -> tuple[Assignment, float, int]:
    """Return the first goal at the shallowest depth; costs may be nonuniform."""
    return _search(prices, "bfs", trip_cost)


def uniform_cost_search(
    prices: PriceOptions, trip_cost: float = 0.0
) -> tuple[Assignment, float, int]:
    """Expand states in accumulated basket-plus-trip cost order."""
    return _search(prices, "ucs", trip_cost)


def a_star_search(
    prices: PriceOptions, trip_cost: float = 0.0
) -> tuple[Assignment, float, int]:
    """Expand by accumulated cost plus the admissible remaining-item bound."""
    return _search(prices, "astar", trip_cost)


def depth_first_search(
    prices: PriceOptions, trip_cost: float = 0.0
) -> tuple[Assignment, float, int]:
    """Return the first goal in depth-first traversal order."""
    return _search(prices, "dfs", trip_cost)


def greedy_best_first_search(
    prices: PriceOptions, trip_cost: float = 0.0
) -> tuple[Assignment, float, int]:
    """Prioritize only the estimated remaining item price; not guaranteed optimal."""
    return _search(prices, "greedy", trip_cost)


def iterative_deepening_search(
    prices: PriceOptions, trip_cost: float = 0.0
) -> tuple[Assignment, float, int]:
    """Repeat depth-limited search with increasing depth limits."""
    return _search(prices, "iddfs", trip_cost)
