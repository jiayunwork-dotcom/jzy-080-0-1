"""Discounting of the cashflow ladder and the dirty (full) price."""

from __future__ import annotations

from dataclasses import dataclass

from .cashflows import Cashflow


@dataclass(frozen=True)
class DiscountedCashflow:
    """A cashflow paired with its discount factor and present value."""

    cashflow: Cashflow
    discount_factor: float
    present_value: float


def discount_factor(per_period_rate: float, period: int) -> float:
    """(1 + r) ** -period.

    Strictly positive for every period because validation guarantees
    ``1 + per_period_rate > 0``.
    """
    return 1.0 / (1.0 + per_period_rate) ** period


def discount_cashflows(
    ladder: list[Cashflow],
    per_period_rate: float,
) -> list[DiscountedCashflow]:
    """Discount every rung of the ladder at the per-period rate."""
    discounted: list[DiscountedCashflow] = []
    for cf in ladder:
        df = discount_factor(per_period_rate, cf.period)
        discounted.append(
            DiscountedCashflow(cashflow=cf, discount_factor=df, present_value=cf.amount * df)
        )
    return discounted


def dirty_price(discounted: list[DiscountedCashflow]) -> float:
    """Full (dirty) price: the sum of every period's present value."""
    return sum(d.present_value for d in discounted)
