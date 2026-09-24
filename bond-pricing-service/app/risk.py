"""Macaulay duration, modified duration and convexity.

All three measures share the pricer's compounding convention so the
numbers stay mutually consistent:

* times are measured in *years* (period / frequency);
* the per-period rate is r = ytm / frequency;
* Macaulay duration = sum(time_years * PV) / dirty price;
* modified duration = Macaulay duration / (1 + r);
* convexity = sum(k(k+1)/m^2 * PV) / dirty price / (1 + r)^2, where k is
  the 1-based period index and m the payment frequency — i.e. the
  period-based second-order weight, scaled back to annual units.

With these definitions, modified duration = -(1/P) dP/dy and
convexity = (1/P) d2P/dy2 exactly, which the test-suite verifies against
finite differences of the pricer itself.
"""

from __future__ import annotations

from .pricing import DiscountedCashflow


def macaulay_duration(discounted: list[DiscountedCashflow], price: float) -> float:
    """PV-weighted average time (in years) of the cashflows."""
    weighted_time = sum(d.cashflow.time_years * d.present_value for d in discounted)
    return weighted_time / price


def modified_duration(macaulay: float, per_period_rate: float) -> float:
    """Macaulay duration divided by (1 + per-period rate)."""
    return macaulay / (1.0 + per_period_rate)


def convexity(
    discounted: list[DiscountedCashflow],
    price: float,
    per_period_rate: float,
    frequency: int,
) -> float:
    """Second-order price sensitivity, annualised, same convention as duration."""
    m = frequency
    weighted = sum(
        (d.cashflow.period * (d.cashflow.period + 1) / (m * m)) * d.present_value
        for d in discounted
    )
    return weighted / price / (1.0 + per_period_rate) ** 2
