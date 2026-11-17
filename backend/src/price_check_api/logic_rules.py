"""Explainable propositional and knowledge-based reasoning over listing evidence."""

from __future__ import annotations

from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from itertools import product
from statistics import median

from .fuzzy_listings import deal_position
from .listing_groups import ComparableGroup
from .listings import Listing, parse_pack_size


@dataclass(frozen=True)
class Rule:
    """A propositional implication whose antecedents may include explicit negation."""

    name: str
    antecedents: tuple[str, ...]
    consequent: str


@dataclass(frozen=True)
class KnowledgeBase:
    """Facts and Horn clauses used by forward, backward, and truth-table reasoning."""

    facts: frozenset[str]
    rules: tuple[Rule, ...]


DEFAULT_RULES = (
    Rule(
        "discount-and-below-median-unit-price",
        ("ON_DISCOUNT", "BELOW_MEDIAN_UNIT_PRICE"),
        "GOOD_DEAL",
    ),
    Rule("high-fuzzy-deal-position", ("FUZZY_DEAL_HIGH",), "GOOD_DEAL"),
    Rule("same-pack-size-implies-comparable", ("SAME_PACK_SIZE",), "COMPARABLE"),
    Rule("same-product-implies-comparable", ("SAME_PRODUCT",), "COMPARABLE"),
    Rule("stock-not-confirmed", ("NOT STOCK_CONFIRMED",), "IN_STOCK_UNKNOWN"),
    Rule("regular-price-not-recorded", ("NOT REGULAR_PRICE_KNOWN",), "DISCOUNT_UNVERIFIED"),
)


def forward_chain(
    facts: Iterable[str],
    rules: Sequence[Rule] = DEFAULT_RULES,
) -> tuple[set[str], list[str]]:
    """Apply forward chaining until no Horn rule can add another proposition."""
    known = set(facts)
    fired: list[str] = []
    applied: set[str] = set()
    changed = True
    while changed:
        changed = False
        for rule in rules:
            if rule.name in applied:
                continue
            if all(literal in known for literal in rule.antecedents):
                known.add(rule.consequent)
                applied.add(rule.name)
                fired.append(rule.name)
                changed = True
    return known, fired


def backward_chain(
    facts: Iterable[str],
    query: str,
    rules: Sequence[Rule] = DEFAULT_RULES,
) -> tuple[bool, list[str]]:
    """Prove a proposition recursively by backward chaining through Horn clauses."""
    known = set(facts)
    trace: list[str] = []
    proving: set[str] = set()

    def prove(proposition: str) -> bool:
        if proposition in known:
            return True
        if proposition in proving:
            return False
        proving.add(proposition)
        try:
            for rule in rules:
                if rule.consequent == proposition and all(
                    prove(antecedent) for antecedent in rule.antecedents
                ):
                    trace.append(rule.name)
                    return True
            return False
        finally:
            proving.remove(proposition)

    return prove(query), trace


def _literal_value(literal: str, assignment: dict[str, bool]) -> bool:
    if literal.startswith("NOT "):
        return not assignment[literal[4:]]
    return assignment[literal]


def entails(kb: KnowledgeBase, query: str) -> bool:
    """Check propositional entailment by truth-table enumeration for small KBs."""
    atoms = {query[4:] if query.startswith("NOT ") else query}
    for rule in kb.rules:
        atoms.add(
            rule.consequent[4:] if rule.consequent.startswith("NOT ") else rule.consequent
        )
        atoms.update(
            antecedent[4:] if antecedent.startswith("NOT ") else antecedent
            for antecedent in rule.antecedents
        )
    atoms.update(
        fact[4:] if fact.startswith("NOT ") else fact for fact in kb.facts
    )
    if len(atoms) > 16:
        raise ValueError("truth-table entailment is limited to 16 propositions")
    for values in product((False, True), repeat=len(atoms)):
        assignment = dict(zip(sorted(atoms), values, strict=True))
        if not all(_literal_value(fact, assignment) for fact in kb.facts):
            continue
        if any(
            all(_literal_value(item, assignment) for item in rule.antecedents)
            and not _literal_value(rule.consequent, assignment)
            for rule in kb.rules
        ):
            continue
        if not _literal_value(query, assignment):
            return False
    return True


def listing_facts(listing: Listing, group: ComparableGroup | None) -> set[str]:
    """Derive evidence propositions from a listing and its observed comparison group."""
    facts = {"NOT STOCK_CONFIRMED"}
    if listing.regular_price_kes is not None:
        facts.add("REGULAR_PRICE_KNOWN")
    else:
        facts.add("NOT REGULAR_PRICE_KNOWN")
    if listing.discount_pct is not None and listing.discount_pct > 0:
        facts.add("ON_DISCOUNT")

    if group is None:
        return facts

    peers = [item for item in group.listings if item.id != listing.id]
    own_size = parse_pack_size(listing.pack_size)
    if own_size and any(parse_pack_size(peer.pack_size) == own_size for peer in peers):
        facts.add("SAME_PACK_SIZE")
    if group.basis == "same product":
        facts.add("SAME_PRODUCT")
    comparable_prices = [
        item.unit_price for item in group.listings if item.unit_price is not None
    ]
    if (
        listing.unit_price is not None
        and len(comparable_prices) > 1
        and listing.unit_price < median(comparable_prices)
    ):
        facts.add("BELOW_MEDIAN_UNIT_PRICE")
    fuzzy = deal_position(listing.discount_pct, listing.unit_price, comparable_prices)
    if fuzzy.label == "high":
        facts.add("FUZZY_DEAL_HIGH")
    return facts


def reason_about_listing(listing: Listing, group: ComparableGroup | None) -> dict[str, object]:
    """Return forward/backward proof traces without asserting stock or checkout facts."""
    facts = listing_facts(listing, group)
    kb = KnowledgeBase(facts=frozenset(facts), rules=DEFAULT_RULES)
    known, fired = forward_chain(facts)
    query = "GOOD_DEAL"
    proved, proof = backward_chain(facts, query)
    if not proved and "COMPARABLE" in known:
        query = "COMPARABLE"
        proved, proof = backward_chain(facts, query)
    conclusion = query if proved else "NO_SUPPORTED_CONCLUSION"
    return {
        "listing_id": listing.id,
        "facts": sorted(facts),
        "derived_facts": sorted(known - facts),
        "fired_rules": fired,
        "backward_proof": proof,
        "conclusion": conclusion,
        "conclusion_supported": proved,
        "reason": (
            "Rules summarize this dated advertised snapshot; stock and checkout price "
            "are not verified."
        ),
        "entailment_checked": (
            entails(kb, conclusion) if conclusion != "NO_SUPPORTED_CONCLUSION" else False
        ),
    }
