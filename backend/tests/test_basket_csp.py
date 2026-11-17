from price_check_api.basket_csp import solve_basket_csp


def test_csp_finds_lowest_feasible_store_assignment() -> None:
    result = solve_basket_csp(
        {
            "bread": {"Naivas": 100, "Quickmart": 125},
            "milk": {"Naivas": 50, "Quickmart": 45},
        },
        max_stores=1,
        budget_cap=160,
    )

    assert result.assignment == {"bread": "Naivas", "milk": "Naivas"}
    assert result.total == 150
    assert result.violated_constraint is None


def test_csp_reports_unsatisfiable_stock_and_store_constraints() -> None:
    result = solve_basket_csp(
        {"bread": {"Naivas": 20}, "milk": {"Quickmart": 30}},
        max_stores=1,
    )

    assert result.assignment is None
    assert result.total is None
    assert result.violated_constraint == "maximum number of stores"


def test_mrv_expands_fewer_nodes_than_fixed_variable_order() -> None:
    domains = {
        "broad": {"A": 1, "B": 2, "C": 3, "D": 4},
        "other": {"A": 1, "B": 2, "C": 3, "D": 4},
        "narrow": {"D": 4},
    }

    mrv = solve_basket_csp(domains, max_stores=1, use_mrv=True)
    naive = solve_basket_csp(domains, max_stores=1, use_mrv=False)

    assert mrv.assignment is not None
    assert mrv.nodes_expanded < naive.nodes_expanded
