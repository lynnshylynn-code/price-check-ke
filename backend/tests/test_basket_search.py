import pytest

from price_check_api.basket_search import a_star_search, breadth_first_search, uniform_cost_search


@pytest.fixture
def prices():
    return [
        {"A": 2.0, "B": 4.0},
        {"A": 8.0, "B": 3.0},
        {"A": 2.0, "B": 5.0},
    ]


def test_algorithms_agree_and_expansion_order(prices):
    bfs = breadth_first_search(prices)
    ucs = uniform_cost_search(prices)
    astar = a_star_search(prices)
    assert bfs[1] == ucs[1] == astar[1] == 7.0
    assert astar[2] <= ucs[2] <= bfs[2]


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
