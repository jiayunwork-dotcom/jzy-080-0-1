"""Composition layer: validation -> ladder -> pricing -> risk -> sensitivity.

Everything here is a pure function of its arguments — no module-level
mutable state — so concurrent requests never share or overwrite each
other's intermediate results.
"""

from __future__ import annotations

from types import SimpleNamespace

from . import cashflows, pricing, risk, sensitivity
from .pricing import DiscountedCashflow
from .validation import BondLike, ValidatedBond, validate_bond, validate_yield_shift


def _validate_and_discount(
    params: BondLike,
) -> tuple[ValidatedBond, list[DiscountedCashflow], float]:
    """Shared pipeline: validate, build the ladder, discount it, sum the price."""
    bond = validate_bond(params)
    ladder = cashflows.build_cashflow_ladder(
        face_value=bond.face_value,
        coupon_per_period=bond.per_period_coupon,
        periods=bond.periods,
        frequency=bond.frequency,
    )
    discounted = pricing.discount_cashflows(ladder, bond.per_period_rate)
    return bond, discounted, pricing.dirty_price(discounted)


def price_bond(params: BondLike) -> dict:
    """Dirty price plus the per-period present-value breakdown."""
    bond, discounted, price = _validate_and_discount(params)
    return {
        "input": params,
        "periods": bond.periods,
        "per_period_rate": bond.per_period_rate,
        "dirty_price": price,
        "cashflows": [
            {
                "period": d.cashflow.period,
                "time_years": d.cashflow.time_years,
                "cashflow": d.cashflow.amount,
                "discount_factor": d.discount_factor,
                "present_value": d.present_value,
            }
            for d in discounted
        ],
    }


def risk_metrics(params: BondLike) -> dict:
    """Macaulay duration, modified duration and convexity (plus the price)."""
    bond, discounted, price = _validate_and_discount(params)
    macaulay = risk.macaulay_duration(discounted, price)
    return {
        "input": params,
        "periods": bond.periods,
        "per_period_rate": bond.per_period_rate,
        "dirty_price": price,
        "macaulay_duration": macaulay,
        "modified_duration": risk.modified_duration(macaulay, bond.per_period_rate),
        "convexity": risk.convexity(discounted, price, bond.per_period_rate, bond.frequency),
    }


def sensitivity_analysis(request: BondLike, yield_shift: float) -> dict:
    """First-order, second-order and exact-repriced values after a yield shift.

    The exact figure is produced by re-running the full pricing pipeline at
    the shifted yield — nothing is hardcoded.
    """
    shift = validate_yield_shift(yield_shift)
    base = risk_metrics(request)

    # Re-price from scratch at the shifted yield; validation of the shifted
    # yield (e.g. discount factors must stay positive) happens here too.
    shifted_params = SimpleNamespace(
        face_value=request.face_value,
        coupon_rate=request.coupon_rate,
        frequency=request.frequency,
        years_to_maturity=request.years_to_maturity,
        ytm=request.ytm + shift,
    )
    exact = price_bond(shifted_params)["dirty_price"]

    price = base["dirty_price"]
    mod_dur = base["modified_duration"]
    conv = base["convexity"]
    first = sensitivity.first_order_price(price, mod_dur, shift)
    second = sensitivity.second_order_price(price, mod_dur, conv, shift)
    return {
        "input": request,
        "yield_shift": shift,
        "shifted_ytm": request.ytm + shift,
        "base_dirty_price": price,
        "modified_duration": mod_dur,
        "convexity": conv,
        "first_order_estimate": first,
        "second_order_estimate": second,
        "exact_reprice": exact,
        "first_order_error": first - exact,
        "second_order_error": second - exact,
    }
