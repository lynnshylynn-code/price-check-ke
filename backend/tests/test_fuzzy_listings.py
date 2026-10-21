import pytest

from price_check_api.fuzzy_listings import deal_position
from price_check_api.fuzzy_price import triangular_membership


@pytest.mark.parametrize(
    ("value", "left", "peak", "right", "expected"),
    [(0, 0, 0, 10, 1), (5, 0, 5, 10, 1), (10, 0, 10, 10, 1),
     (-1, 0, 5, 10, 0), (11, 0, 5, 10, 0)],
)
def test_triangular_membership_boundaries_and_peaks(value, left, peak, right, expected):
    assert triangular_membership(value, left, peak, right) == expected


def test_deal_position_defuzzifies_to_snapshot_label():
    result = deal_position(35.0, 10.0, [8.0, 10.0, 12.0, 16.0])
    assert result.score is not None
    assert result.label in {"low", "typical", "high"}
    assert "not buying advice" in result.reason
    assert result.group_percentiles is not None


def test_missing_regular_price_or_group_returns_reason_without_score():
    no_regular = deal_position(None, 10.0, [8.0, 10.0, 12.0])
    no_group = deal_position(20.0, 10.0, [])
    assert no_regular.score is None and "No regular price" in no_regular.reason
    assert no_group.score is None and "No comparable" in no_group.reason
