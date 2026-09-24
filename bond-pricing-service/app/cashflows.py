"""Construction of the contractual cashflow ladder for a bullet bond."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Cashflow:
    """One contractual payment.

    period:      1-based index of the payment period
    time_years:  payment time in years (period / frequency)
    amount:      coupon amount, plus the face value on the final period
    """

    period: int
    time_years: float
    amount: float


def build_cashflow_ladder(
    *,
    face_value: float,
    coupon_per_period: float,
    periods: int,
    frequency: int,
) -> list[Cashflow]:
    """Equal coupons every period; the last period also repays the face value."""
    ladder: list[Cashflow] = []
    for k in range(1, periods + 1):
        amount = coupon_per_period + (face_value if k == periods else 0.0)
        ladder.append(Cashflow(period=k, time_years=k / frequency, amount=amount))
    return ladder
