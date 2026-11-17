"""Local and adversarial search teaching demonstrations for store assignments."""

from __future__ import annotations

import random
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from math import exp

PriceOptions = Sequence[Mapping[str, float]]
Assignment = tuple[str, ...]


@dataclass(frozen=True)
class LocalSearchResult:
    assignment: Assignment
    cost: float
    steps: int


@dataclass(frozen=True)
class GameSearchResult:
    value: int
    nodes_expanded: int
    action: str | None = None


def _cost(prices: PriceOptions, assignment: Assignment, trip_cost: float) -> float:
    item_cost = sum(prices[index][store] for index, store in enumerate(assignment))
    return item_cost + trip_cost * max(0, len(set(assignment)) - 1)


def _validate(prices: PriceOptions, trip_cost: float) -> None:
    if trip_cost < 0:
        raise ValueError("trip_cost must be non-negative")
    if any(not item for item in prices):
        raise ValueError("each item must have at least one store price")


def hill_climbing(
    prices: PriceOptions,
    *,
    trip_cost: float = 0.0,
    initial_assignment: Assignment | None = None,
    restarts: int = 10,
    max_steps: int = 100,
    seed: int = 42,
) -> LocalSearchResult:
    """Minimize basket cost by hill climbing from seeded random restarts."""
    _validate(prices, trip_cost)
    if restarts < 0 or max_steps < 0:
        raise ValueError("restarts and max_steps must be non-negative")
    if not prices:
        return LocalSearchResult((), 0.0, 0)
    rng = random.Random(seed)
    starts = []
    if initial_assignment is not None:
        if len(initial_assignment) != len(prices) or any(
            store not in prices[index] for index, store in enumerate(initial_assignment)
        ):
            raise ValueError("initial assignment must choose an available store for every item")
        starts.append(initial_assignment)
    starts.append(tuple(min(item, key=item.get) for item in prices))
    starts.extend(
        tuple(rng.choice(sorted(item)) for item in prices) for _ in range(restarts)
    )
    best = min(starts, key=lambda assignment: _cost(prices, assignment, trip_cost))
    steps = 0
    for start in starts:
        current = start
        current_cost = _cost(prices, current, trip_cost)
        for _ in range(max_steps):
            neighbors = []
            for index, item in enumerate(prices):
                for store in sorted(item):
                    if store != current[index]:
                        candidate = (*current[:index], store, *current[index + 1 :])
                        neighbors.append((candidate, _cost(prices, candidate, trip_cost)))
            steps += 1
            if not neighbors:
                break
            neighbor, neighbor_cost = min(neighbors, key=lambda pair: pair[1])
            if neighbor_cost >= current_cost:
                break
            current, current_cost = neighbor, neighbor_cost
        if current_cost < _cost(prices, best, trip_cost):
            best = current
    return LocalSearchResult(best, _cost(prices, best, trip_cost), steps)


def simulated_annealing(
    prices: PriceOptions,
    *,
    trip_cost: float = 0.0,
    initial_assignment: Assignment | None = None,
    initial_temperature: float = 10.0,
    cooling_rate: float = 0.95,
    steps: int = 500,
    seed: int = 42,
) -> LocalSearchResult:
    """Minimize basket cost with seeded simulated annealing and geometric cooling."""
    _validate(prices, trip_cost)
    if initial_temperature <= 0 or not 0 < cooling_rate < 1 or steps < 0:
        raise ValueError(
            "temperature must be positive, cooling_rate in (0, 1), and steps non-negative"
        )
    if not prices:
        return LocalSearchResult((), 0.0, 0)
    rng = random.Random(seed)
    if initial_assignment is None:
        current = tuple(rng.choice(sorted(item)) for item in prices)
    else:
        if len(initial_assignment) != len(prices) or any(
            store not in prices[index] for index, store in enumerate(initial_assignment)
        ):
            raise ValueError("initial assignment must choose an available store for every item")
        current = initial_assignment
    current_cost = _cost(prices, current, trip_cost)
    best, best_cost = current, current_cost
    temperature = initial_temperature
    for _ in range(steps):
        index = rng.randrange(len(prices))
        alternatives = sorted(set(prices[index]) - {current[index]})
        if alternatives:
            store = rng.choice(alternatives)
            candidate = (*current[:index], store, *current[index + 1 :])
            candidate_cost = _cost(prices, candidate, trip_cost)
            delta = candidate_cost - current_cost
            if delta < 0 or rng.random() < exp(-delta / temperature):
                current, current_cost = candidate, candidate_cost
                if current_cost < best_cost:
                    best, best_cost = current, current_cost
        temperature *= cooling_rate
    return LocalSearchResult(best, best_cost, steps)


_PRICING_PAYOFFS = {
    ("discount", "discount"): 3,
    ("discount", "hold price"): 5,
    ("hold price", "discount"): 2,
    ("hold price", "hold price"): 4,
}
_RETAILER_ACTIONS = ("discount", "hold price")


def pricing_game_minimax() -> GameSearchResult:
    """Solve an illustrative, non-predictive two-retailer pricing game by minimax."""
    nodes = 0
    action_values = []
    for first_action in _RETAILER_ACTIONS:
        outcomes = []
        for second_action in _RETAILER_ACTIONS:
            nodes += 1
            outcomes.append(_PRICING_PAYOFFS[(first_action, second_action)])
        action_values.append((first_action, min(outcomes)))
    action, value = max(action_values, key=lambda item: item[1])
    return GameSearchResult(value, nodes, action)


def pricing_game_alpha_beta() -> GameSearchResult:
    """Solve the same teaching game using minimax alpha-beta pruning."""
    nodes = 0
    alpha = float("-inf")
    beta = float("inf")
    best_action = None
    best_value = float("-inf")
    for first_action in _RETAILER_ACTIONS:
        value = float("inf")
        beta = float("inf")
        for second_action in _RETAILER_ACTIONS:
            nodes += 1
            value = min(value, _PRICING_PAYOFFS[(first_action, second_action)])
            beta = min(beta, value)
            if beta <= alpha:
                break
        if value > best_value:
            best_action, best_value = first_action, value
        alpha = max(alpha, best_value)
    return GameSearchResult(int(best_value), nodes, best_action)
