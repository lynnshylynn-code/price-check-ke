import pytest

from price_check_api.association_rules import association_rules, mine_frequent_itemsets


def test_apriori_metrics_match_hand_computed_transactions() -> None:
    transactions = [
        {"bread", "milk"},
        {"bread", "milk"},
        {"bread", "milk"},
        {"bread"},
        {"milk"},
        {"tea"},
    ]

    rules = association_rules(transactions, min_support=0.1, min_confidence=0.1)
    bread_to_milk = next(
        rule for rule in rules if rule.antecedent == {"bread"} and rule.consequent == {"milk"}
    )

    assert bread_to_milk.support == pytest.approx(0.5)
    assert bread_to_milk.confidence == pytest.approx(0.75)
    assert bread_to_milk.lift == pytest.approx(1.125)
    pair_support = mine_frequent_itemsets(transactions, min_support=0.5)[
        frozenset({"bread", "milk"})
    ]
    assert pair_support == 0.5


def test_apriori_rejects_invalid_thresholds() -> None:
    with pytest.raises(ValueError, match="min_support"):
        mine_frequent_itemsets([{"milk"}], min_support=0)
