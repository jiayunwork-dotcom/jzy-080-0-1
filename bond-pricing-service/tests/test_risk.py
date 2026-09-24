"""Duration/convexity invariants and the yield-price monotonicity."""

from __future__ import annotations

import pytest
from conftest import make_params

from app import engine
from app.sample import SAMPLE_BOND


@pytest.mark.parametrize("years", [1.0, 5.0, 7.5, 30.0])
def test_zero_coupon_macaulay_duration_equals_years_to_maturity(years):
    """A zero-coupon bond's Macaulay duration is exactly its maturity."""
    metrics = engine.risk_metrics(make_params(coupon_rate=0.0, years_to_maturity=years))
    assert metrics["macaulay_duration"] == pytest.approx(years, rel=1e-12)


def test_modified_duration_is_macaulay_over_one_plus_period_rate():
    metrics = engine.risk_metrics(make_params())
    r = SAMPLE_BOND["ytm"] / SAMPLE_BOND["frequency"]
    expected = metrics["macaulay_duration"] / (1.0 + r)
    assert metrics["modified_duration"] == pytest.approx(expected, rel=1e-12)


def test_price_falls_when_yield_rises():
    """Monotonicity: lifting only the YTM must lower the dirty price."""
    ytms = [0.01, 0.03, 0.05, 0.08, 0.12]
    prices = [engine.price_bond(make_params(ytm=y))["dirty_price"] for y in ytms]
    assert all(higher > lower for higher, lower in zip(prices, prices[1:]))


def test_coupon_bond_duration_is_below_maturity():
    metrics = engine.risk_metrics(make_params())
    assert 0 < metrics["macaulay_duration"] < SAMPLE_BOND["years_to_maturity"]


def test_convexity_is_positive_for_plain_coupon_bond():
    metrics = engine.risk_metrics(make_params())
    assert metrics["convexity"] > 0


def test_longer_maturity_has_longer_duration():
    short = engine.risk_metrics(make_params(years_to_maturity=3.0))
    long = engine.risk_metrics(make_params(years_to_maturity=10.0))
    assert long["macaulay_duration"] > short["macaulay_duration"]
