import pytest

from price_check_api.basket_search import (
    a_star_search,
    breadth_first_search,
    depth_first_search,
    greedy_best_first_search,
    iterative_deepening_search,
    uniform_cost_search,
)


@pytest.fixture
def prices():
    return [
        {"A": 2.0, "B": 4.0},
        {"A": 8.0, "B": 3.0},
        {"A": 2.0, "B": 5.0},
    ]


def test_cost_searches_are_optimal_and_bfs_returns_first_goal(prices):
    bfs = breadth_first_search(prices)
    ucs = uniform_cost_search(prices)
    astar = a_star_search(prices)
    assert ucs[1] == astar[1] == 7.0
    assert bfs[1] >= ucs[1]
    assert bfs[2] > 0
    assert astar[2] <= ucs[2]


def test_trip_cost_can_make_single_store_optimal():
    prices = [{"A": 1.0, "B": 9.0}, {"A": 9.0, "B": 1.0}]
    assignment, cost, _ = uniform_cost_search(prices, trip_cost=9.0)
    assert assignment == ("A", "A")
    assert cost == 10.0


def test_empty_and_one_item_baskets():
    assert a_star_search([]) == ((), 0.0, 0)
    assignment, cost, _ = a_star_search([{"A": 4.0, "B": 2.0}])
    assert assignment == ("B",)
    assert cost == 2.0


def test_all_six_searches_return_complete_assignments(prices):
    for search in (breadth_first_search, depth_first_search, uniform_cost_search,
                   iterative_deepening_search, greedy_best_first_search, a_star_search):
        assignment, cost, expanded = search(prices)
        assert len(assignment) == len(prices)
        assert cost >= 0
        assert expanded > 0


def test_greedy_can_return_a_nonoptimal_basket():
    prices = [{"A": 10.0, "B": 1.0}, {"A": 10.0, "B": 1.0}]
    assert greedy_best_first_search(prices)[1] == 20.0
    assert uniform_cost_search(prices)[1] == a_star_search(prices)[1] == 2.0
