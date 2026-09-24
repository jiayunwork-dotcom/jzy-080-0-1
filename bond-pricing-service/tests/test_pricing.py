"""Pricing invariants: par bond, zero-coupon bond, PV breakdown."""

from __future__ import annotations

import pytest
from conftest import make_params

from app import engine
from app.sample import SAMPLE_BOND

FACE = SAMPLE_BOND["face_value"]


def test_par_bond_prices_to_face_value():
    """Coupon rate == YTM  =>  dirty price == face value."""
    result = engine.price_bond(make_params())
    assert result["dirty_price"] == pytest.approx(FACE, rel=1e-12)


@pytest.mark.parametrize("frequency", [1, 2, 4, 12])
def test_par_bond_prices_to_par_at_every_frequency(frequency):
    """Densifying the payment grid keeps a par bond exactly at par."""
    result = engine.price_bond(make_params(frequency=frequency))
    assert result["dirty_price"] == pytest.approx(FACE, rel=1e-12)


def test_dirty_price_equals_sum_of_present_values():
    """The headline price is exactly the sum of the per-period PV detail."""
    result = engine.price_bond(make_params(coupon_rate=0.06, ytm=0.045))
    total = sum(cf["present_value"] for cf in result["cashflows"])
    assert result["dirty_price"] == pytest.approx(total, rel=1e-12)


def test_final_cashflow_includes_face_value_and_coupon():
    result = engine.price_bond(make_params())
    final = result["cashflows"][-1]
    per_period_coupon = FACE * SAMPLE_BOND["coupon_rate"] / SAMPLE_BOND["frequency"]
    assert final["cashflow"] == pytest.approx(per_period_coupon + FACE, rel=1e-12)
    assert len(result["cashflows"]) == 10  # 5 years x 2 payments


def test_zero_coupon_price_is_discounted_face_value():
    result = engine.price_bond(make_params(coupon_rate=0.0))
    expected = FACE / (1.0 + SAMPLE_BOND["ytm"] / 2) ** 10
    assert result["dirty_price"] == pytest.approx(expected, rel=1e-12)


def test_premium_bond_matches_closed_form_annuity():
    """6% coupon vs 5% yield, 5Y semi-annual: textbook annuity formula."""
    result = engine.price_bond(make_params(coupon_rate=0.06))
    r, n = 0.05 / 2, 10
    annuity = (1.0 - (1.0 + r) ** -n) / r
    expected = FACE * 0.06 / 2 * annuity + FACE * (1.0 + r) ** -n
    assert result["dirty_price"] == pytest.approx(expected, rel=1e-12)
    assert result["dirty_price"] > FACE  # coupon above yield => premium


def test_discount_bond_prices_below_par():
    result = engine.price_bond(make_params(coupon_rate=0.03))
    assert result["dirty_price"] < FACE
