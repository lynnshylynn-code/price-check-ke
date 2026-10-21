"""Snapshot-relative fuzzy score combining discount and comparable unit-price position."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from .fuzzy_price import _percentile, triangular_membership

DealLabel = Literal["low", "typical", "high"]


@dataclass(frozen=True)
class ListingDealPosition:
    score: float | None
    label: DealLabel | None
    reason: str
    discount_memberships: dict[str, float] | None = None
    price_memberships: dict[str, float] | None = None
    group_percentiles: dict[str, float] | None = None


def deal_position(
    discount_pct: float | None,
    unit_price: float | None,
    comparable_unit_prices: list[float],
) -> ListingDealPosition:
    if discount_pct is None:
        return ListingDealPosition(
            None, None, "No regular price is recorded; discount-based position is unavailable."
        )
    if unit_price is None or not comparable_unit_prices:
        return ListingDealPosition(
            None, None, "No comparable unit-price group is available for this listing."
        )
    values = [value for value in comparable_unit_prices if value > 0]
    if not values:
        return ListingDealPosition(
            None, None, "No comparable unit-price group is available for this listing."
        )
    p10, p50, p90 = (_percentile(values, amount) for amount in (.1, .5, .9))
    discount = {
        "small": triangular_membership(discount_pct, 0, 0, 15),
        "medium": triangular_membership(discount_pct, 5, 25, 45),
        "large": triangular_membership(discount_pct, 30, 100, 100),
    }
    price = {
        "low": triangular_membership(unit_price, p10, p10, p50),
        "typical": triangular_membership(unit_price, p10, p50, p90),
        "high": triangular_membership(unit_price, p50, p90, p90),
    }
    # Rules use Mamdani min implication; consequents are max-aggregated below.
    rule_activations = [
        (min(discount["large"], price["low"]), "high"),
        (min(discount["medium"], price["low"]), "high"),
        (min(discount["large"], price["typical"]), "high"),
        (min(discount["medium"], price["typical"]), "typical"),
        (min(discount["small"], price["low"]), "typical"),
        (min(discount["small"], price["typical"]), "typical"),
        (max(price.values()), "low"),
    ]
    shapes = {"low": (0, 0, 40), "typical": (25, 50, 75), "high": (60, 100, 100)}
    output = [0.0] * 101
    for activation, term in rule_activations:
        left, peak, right = shapes[term]
        for score in range(101):
            output[score] = max(
                output[score],
                min(activation, triangular_membership(score, left, peak, right)),
            )
    mass = sum(output)
    if mass == 0:
        return ListingDealPosition(
            None, None, "Available snapshot evidence does not support a deal-position score."
        )
    score = sum(index * weight for index, weight in enumerate(output)) / mass
    label: DealLabel = "low" if score < 33.33 else "typical" if score < 66.67 else "high"
    return ListingDealPosition(
        score,
        label,
        "Relative position within this snapshot only; not buying advice.",
        discount,
        price,
        {"p10": p10, "p50": p50, "p90": p90},
    )
