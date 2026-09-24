"""Convention self-consistency, in particular under densified frequencies.

The same annualised convention must hold at every payment frequency:
modified duration and convexity reported by the engine must equal the
first and second derivatives of the engine's *own* price function.
"""

from __future__ import annotations

import pytest
from conftest import make_params

from app import engine

H = 1e-4  # 1bp yield bump for central finite differences


def _price(**overrides) -> float:
    return engine.price_bond(make_params(**overrides))["dirty_price"]


@pytest.mark.parametrize("frequency", [1, 2, 4, 12])
def test_duration_matches_numerical_derivative(frequency):
    base = dict(frequency=frequency, coupon_rate=0.06, ytm=0.05, years_to_maturity=7.0)
    metrics = engine.risk_metrics(make_params(**base))
    up = _price(**{**base, "ytm": base["ytm"] + H})
    down = _price(**{**base, "ytm": base["ytm"] - H})
    numerical_mod_dur = -(up - down) / (2.0 * H) / metrics["dirty_price"]
    assert metrics["modified_duration"] == pytest.approx(numerical_mod_dur, rel=1e-6)


@pytest.mark.parametrize("frequency", [1, 2, 4, 12])
def test_convexity_matches_numerical_second_derivative(frequency):
    base = dict(frequency=frequency, coupon_rate=0.06, ytm=0.05, years_to_maturity=7.0)
    metrics = engine.risk_metrics(make_params(**base))
    up = _price(**{**base, "ytm": base["ytm"] + H})
    down = _price(**{**base, "ytm": base["ytm"] - H})
    numerical_convexity = (up - 2.0 * metrics["dirty_price"] + down) / (H * H) / metrics["dirty_price"]
    assert metrics["convexity"] == pytest.approx(numerical_convexity, rel=1e-5)


def test_doubling_frequency_doubles_cashflow_count():
    semi = engine.price_bond(make_params(frequency=2))
    quarterly = engine.price_bond(make_params(frequency=4))
    assert len(quarterly["cashflows"]) == 2 * len(semi["cashflows"])


@pytest.mark.parametrize("frequency", [1, 2, 4, 12])
def test_price_remains_sum_of_pvs_when_frequency_densified(frequency):
    """Same annual coupon and yield, denser grid: price stays self-consistent."""
    result = engine.price_bond(make_params(frequency=frequency, coupon_rate=0.06, ytm=0.05))
    total = sum(cf["present_value"] for cf in result["cashflows"])
    assert result["dirty_price"] == pytest.approx(total, rel=1e-12)
    # Per-period quantities use the same per-period rate everywhere.
    r = 0.05 / frequency
    for cf in result["cashflows"]:
        assert cf["discount_factor"] == pytest.approx((1.0 + r) ** -cf["period"], rel=1e-12)
