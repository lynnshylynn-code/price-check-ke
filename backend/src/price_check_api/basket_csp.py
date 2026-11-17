"""Backtracking constraint satisfaction for basket assignments across observed stores."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass

PriceDomains = Mapping[str, Mapping[str, float]]


@dataclass(frozen=True)
class CSPResult:
    assignment: dict[str, str] | None
    total: float | None
    nodes_expanded: int
    violated_constraint: str | None = None


def solve_basket_csp(
    domains: PriceDomains,
    *,
    max_stores: int | None = None,
    min_spend_per_store: float = 0.0,
    budget_cap: float | None = None,
    must_use_store: str | None = None,
    use_mrv: bool = True,
) -> CSPResult:
    """Use MRV backtracking and forward checking to satisfy basket constraints."""
    if not domains:
        raise ValueError("basket must contain at least one item")
    if any(not choices for choices in domains.values()):
        return CSPResult(None, None, 0, "an item has no observed store price")
    if max_stores is not None and max_stores < 1:
        raise ValueError("max_stores must be at least one")
    if min_spend_per_store < 0 or (budget_cap is not None and budget_cap < 0):
        raise ValueError("spend limits must be non-negative")
    if any(price < 0 for choices in domains.values() for price in choices.values()):
        raise ValueError("prices must be non-negative")

    variables = tuple(domains)
    assigned: dict[str, str] = {}
    best_assignment: dict[str, str] | None = None
    best_total = float("inf")
    nodes_expanded = 0
    violations: set[str] = set()

    def line_total(variable: str, store: str) -> float:
        return float(domains[variable][store])

    def possible_domains(unassigned: list[str]) -> dict[str, list[str]]:
        used = set(assigned.values())
        remaining: dict[str, list[str]] = {}
        for variable in unassigned:
            choices = []
            for store in sorted(domains[variable]):
                if (
                    store not in used
                    and max_stores is not None
                    and len(used) >= max_stores
                ):
                    continue
                choices.append(store)
            remaining[variable] = choices
        return remaining

    def visit() -> None:
        nonlocal nodes_expanded, best_assignment, best_total
        nodes_expanded += 1
        assigned_total = sum(line_total(item, store) for item, store in assigned.items())
        if budget_cap is not None and assigned_total > budget_cap:
            violations.add("budget cap")
            return
        if assigned_total >= best_total:
            return

        unassigned = [item for item in variables if item not in assigned]
        if not unassigned:
            totals: dict[str, float] = {}
            for item, store in assigned.items():
                totals[store] = totals.get(store, 0.0) + line_total(item, store)
            if must_use_store and must_use_store not in totals:
                violations.add(f"must use store {must_use_store}")
                return
            if any(total < min_spend_per_store for total in totals.values()):
                violations.add("per-store minimum spend")
                return
            best_assignment = assigned.copy()
            best_total = assigned_total
            return

        domains_now = possible_domains(unassigned)
        if any(not choices for choices in domains_now.values()):
            violations.add("maximum number of stores")
            return
        if (
            must_use_store
            and must_use_store not in assigned.values()
            and not any(must_use_store in choices for choices in domains_now.values())
        ):
            violations.add(f"must use store {must_use_store}")
            return
        lower_bound = assigned_total + sum(
            min(line_total(item, store) for store in domains_now[item])
            for item in unassigned
        )
        if budget_cap is not None and lower_bound > budget_cap:
            violations.add("budget cap")
            return

        selected_totals: dict[str, float] = {}
        for item, store in assigned.items():
            selected_totals[store] = selected_totals.get(store, 0.0) + line_total(item, store)
        for store, current in selected_totals.items():
            maximum_additional = sum(
                line_total(item, store) if store in domains_now[item] else 0.0
                for item in unassigned
            )
            if current + maximum_additional < min_spend_per_store:
                violations.add("per-store minimum spend")
                return

        variable = (
            min(unassigned, key=lambda item: (len(domains_now[item]), variables.index(item)))
            if use_mrv
            else unassigned[0]
        )
        for store in domains_now[variable]:
            assigned[variable] = store
            visit()
            del assigned[variable]

    visit()
    if best_assignment is not None:
        return CSPResult(best_assignment, best_total, nodes_expanded)
    reason = (
        sorted(violations)[0]
        if violations
        else "no consistent assignment satisfies the supplied constraints"
    )
    return CSPResult(None, None, nodes_expanded, reason)
