from unittest.mock import patch
import pytest
from src.analytics import (
    calculate_growth,
    calculate_growth_yoy,
    calculate_growth_mom,
    calculate_growth_wow,
)


@pytest.mark.parametrize(
    "current, previous, expected",
    [
        (150, 100, 50.0),
        (80, 100, -20.0),
        (100, 100, 0.0),
        (0, 0, 0.0),
        (50, 0, 100.0),
        (-10, 0, 0.0),
        (133.333, 100, 33.33),
    ],
)
def test_all_growth_functions_identical(current, previous, expected):
    assert calculate_growth(current, previous) == expected
    assert calculate_growth(current, previous, period="custom") == expected
    assert calculate_growth_yoy(current, previous) == expected
    assert calculate_growth_mom(current, previous) == expected
    assert calculate_growth_wow(current, previous) == expected


@pytest.mark.parametrize(
    "wrapper_fn, expected_period",
    [
        (calculate_growth_yoy, "yoy"),
        (calculate_growth_mom, "mom"),
        (calculate_growth_wow, "wow"),
    ],
)
def test_growth_wrappers_delegate_to_base(wrapper_fn, expected_period):
    with patch("src.analytics.calculate_growth", return_value=25.0) as mock_base:
        result = wrapper_fn(125, 100)
        assert result == 25.0
        mock_base.assert_called_once_with(125, 100, period=expected_period)