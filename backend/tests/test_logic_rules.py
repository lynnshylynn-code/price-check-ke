from price_check_api.logic_rules import (
    KnowledgeBase,
    Rule,
    backward_chain,
    entails,
    forward_chain,
)


def test_forward_chaining_applies_modus_ponens() -> None:
    facts, trace = forward_chain({"A"}, (Rule("A-implies-B", ("A",), "B"),))

    assert "B" in facts
    assert trace == ["A-implies-B"]


def test_forward_and_backward_chaining_agree() -> None:
    rules = (
        Rule("discount-and-cheap", ("ON_DISCOUNT", "BELOW_MEDIAN_UNIT_PRICE"), "GOOD_DEAL"),
    )
    initial = {"ON_DISCOUNT", "BELOW_MEDIAN_UNIT_PRICE"}

    forward, _ = forward_chain(initial, rules)
    backward, trace = backward_chain(initial, "GOOD_DEAL", rules)

    assert "GOOD_DEAL" in forward
    assert backward is True
    assert trace == ["discount-and-cheap"]


def test_truth_table_entailment_checks_models() -> None:
    knowledge = KnowledgeBase(
        frozenset({"A"}),
        (Rule("modus-ponens", ("A",), "B"),),
    )

    assert entails(knowledge, "B") is True
    assert entails(knowledge, "C") is False


def test_explicit_negation_can_fire_a_rule() -> None:
    rules = (Rule("missing-stock-evidence", ("NOT STOCK_CONFIRMED",), "IN_STOCK_UNKNOWN"),)

    facts, trace = forward_chain({"NOT STOCK_CONFIRMED"}, rules)

    assert "IN_STOCK_UNKNOWN" in facts
    assert trace == ["missing-stock-evidence"]
