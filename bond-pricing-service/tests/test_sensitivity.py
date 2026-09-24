"""First/second-order sensitivity estimates versus exact repricing."""

from __future__ import annotations

import pytest
from conftest import make_params

from app import engine
from app.sample import SAMPLE_BOND


def _sensitivity(shift: float, **overrides) -> dict:
    return engine.sensitivity_analysis(make_params(**overrides), shift)


def test_second_order_beats_first_order_when_yield_rises():
    """+100bp: the convexity-corrected estimate must track the exact reprice
    more closely than the duration-only one (the price falls less)."""
    result = _sensitivity(0.01)
    assert result["first_order_estimate"] < result["exact_reprice"]
    assert result["second_order_estimate"] > result["first_order_estimate"]
    assert abs(result["second_order_error"]) < abs(result["first_order_error"])


def test_second_order_beats_first_order_when_yield_falls():
    """-100bp: duration-only understates the rise; the (always positive)
    convexity term lifts the estimate back toward the exact reprice."""
    result = _sensitivity(-0.01)
    assert result["first_order_estimate"] < result["exact_reprice"]
    assert result["second_order_estimate"] > result["first_order_estimate"]
    assert abs(result["second_order_error"]) < abs(result["first_order_error"])


@pytest.mark.parametrize("shift", [0.005, 0.01, 0.02])
def test_second_order_is_closer_across_upward_shift_sizes(shift):
    result = _sensitivity(shift)
    assert abs(result["second_order_error"]) < abs(result["first_order_error"])


def test_estimates_converge_to_exact_for_tiny_shifts():
    """For a 1bp shift both estimates nearly coincide with the exact reprice,
    and the second-order error is orders of magnitude smaller."""
    result = _sensitivity(0.0001)
    assert abs(result["second_order_error"]) < 1e-6
    assert abs(result["second_order_error"]) < abs(result["first_order_error"])


def test_exact_reprice_is_recomputed_not_hardcoded():
    """The exact figure must equal a fresh pricing run at the shifted yield."""
    shift = 0.015
    result = _sensitivity(shift)
    recomputed = engine.price_bond(make_params(ytm=SAMPLE_BOND["ytm"] + shift))
    assert result["exact_reprice"] == pytest.approx(recomputed["dirty_price"], rel=1e-12)
    assert result["shifted_ytm"] == pytest.approx(SAMPLE_BOND["ytm"] + shift, rel=1e-12)


def test_zero_shift_returns_base_price_for_all_three():
    result = _sensitivity(0.0)
    base = engine.price_bond(make_params())["dirty_price"]
    assert result["first_order_estimate"] == pytest.approx(base, rel=1e-12)
    assert result["second_order_estimate"] == pytest.approx(base, rel=1e-12)
    assert result["exact_reprice"] == pytest.approx(base, rel=1e-12)
