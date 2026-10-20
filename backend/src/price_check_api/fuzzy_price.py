"""Transparent fuzzy description of a price's position in observed history."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

PriceLabel = Literal["low", "typical", "high"]


@dataclass(frozen=True)
class PricePosition:
    score: float | None
    label: PriceLabel | None
    reason: str
    p10: float | None = None
    p50: float | None = None
    p90: float | None = None
    memberships: dict[str, float] | None = None


def triangular_membership(value: float, left: float, peak: float, right: float) -> float:
    """Triangle membership with shoulder support for degenerate endpoints."""
    if not left <= peak <= right:
        raise ValueError("expected left <= peak <= right")
    if left == peak == right:
        return 1.0 if value == peak else 0.0
    if value == peak:
        return 1.0
    if value < peak:
        if left == peak:
            return 1.0
        return max(0.0, min(1.0, (value - left) / (peak - left)))
    if peak == right:
        return 1.0
    return max(0.0, min(1.0, (right - value) / (right - peak)))


def _percentile(values: list[float], fraction: float) -> float:
    ordered = sorted(values)
    position = (len(ordered) - 1) * fraction
    lower = int(position)
    upper = min(lower + 1, len(ordered) - 1)
    weight = position - lower
    return ordered[lower] * (1 - weight) + ordered[upper] * weight


def price_position(
    history: list[float],
    current_price: float,
    trend: Literal["rising", "stable", "falling"] | None = None,
) -> PricePosition:
    """Apply explicit Mamdani rules to the current price and history thresholds."""
    valid = [value for value in history if value >= 0]
    if not valid:
        return PricePosition(
            None, None, "No observed price history is available for this area and commodity."
        )
    p10, p50, p90 = (_percentile(valid, fraction) for fraction in (.1, .5, .9))
    memberships = {
        "low": triangular_membership(current_price, p10, p10, p50),
        "typical": triangular_membership(current_price, p10, p50, p90),
        "high": triangular_membership(current_price, p50, p90, p90),
    }
    # Mamdani implication (min), max aggregation, and centroid defuzzification.
    outputs = [0.0] * 101
    rules = [(memberships["low"], "low"), (memberships["typical"], "typical"),
             (memberships["high"], "high")]
    if trend is not None:
        if trend == "rising":
            rules.append((memberships["typical"], "high"))
        elif trend == "falling":
            rules.append((memberships["typical"], "low"))
        else:
            rules.append((memberships["typical"], "typical"))
    output_shapes = {"low": (0, 0, 50), "typical": (0, 50, 100), "high": (50, 100, 100)}
    for activation, output_term in rules:
        left, peak, right = output_shapes[output_term]
        for score in range(101):
            outputs[score] = max(outputs[score], min(
                activation, triangular_membership(score, left, peak, right)
            ))
    mass = sum(outputs)
    if mass == 0:
        return PricePosition(
            None,
            None,
            "The observed history does not support a fuzzy position score.",
            p10,
            p50,
            p90,
            memberships,
        )
    score = sum(index * membership for index, membership in enumerate(outputs)) / mass
    label: PriceLabel = "low" if score < 33.33 else "typical" if score < 66.67 else "high"
    return PricePosition(
        score,
        label,
        "Historical position only; this is not a forecast or buying recommendation.",
        p10,
        p50,
        p90,
        memberships,
    )
