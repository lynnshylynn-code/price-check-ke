from price_check_api.local_search import (
    hill_climbing,
    pricing_game_alpha_beta,
    pricing_game_minimax,
    simulated_annealing,
)


def test_hill_climbing_with_restarts_does_not_worsen_its_start() -> None:
    prices = [{"A": 1, "B": 8}, {"A": 8, "B": 1}, {"A": 2, "B": 9}]
    initial = ("A", "B", "A")

    result = hill_climbing(prices, initial_assignment=initial, trip_cost=5, seed=7)
    initial_cost = sum(prices[index][store] for index, store in enumerate(initial)) + 5

    assert result.cost <= initial_cost


def test_annealing_is_seeded_and_deterministic() -> None:
    prices = [{"A": 2, "B": 9}, {"A": 8, "B": 1}, {"A": 4, "B": 3}]

    first = simulated_annealing(prices, seed=11)
    second = simulated_annealing(prices, seed=11)

    assert first == second


def test_alpha_beta_matches_minimax_with_fewer_nodes() -> None:
    plain = pricing_game_minimax()
    pruned = pricing_game_alpha_beta()

    assert pruned.value == plain.value
    assert pruned.action == plain.action
    assert pruned.nodes_expanded < plain.nodes_expanded
