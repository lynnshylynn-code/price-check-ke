import pytest

from price_check_api.fuzzy_price import price_position, triangular_membership


def test_triangle_peaks_and_shoulders():
    assert triangular_membership(5, 0, 5, 10) == 1
    assert triangular_membership(2.5, 0, 5, 10) == .5
    assert triangular_membership(-1, 0, 0, 10) == 1
    assert triangular_membership(11, 0, 10, 10) == 1
    assert triangular_membership(11, 0, 5, 10) == 0


def test_percentile_memberships_and_defuzzification():
    result = price_position(list(map(float, range(1, 101))), 80.0, "rising")
    assert result.score is not None
    assert result.label in {"typical", "high"}
    assert result.p10 < result.p50 < result.p90
    assert result.memberships is not None
    assert result.memberships["high"] > 0


def test_empty_history_returns_no_score():
    result = price_position([], 4.0)
    assert result.score is None
    assert result.label is None
    assert "No observed" in result.reason


def test_invalid_triangle_order_is_rejected():
    with pytest.raises(ValueError):
        triangular_membership(1, 3, 2, 4)
