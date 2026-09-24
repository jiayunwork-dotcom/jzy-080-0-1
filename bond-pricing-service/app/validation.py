"""Domain validation for bond pricing inputs.

Every check runs *before* any cashflow is built, so illegal inputs can
never reach the pricing math. Violations raise :class:`BondValidationError`
carrying a structured list of issues; the HTTP layer turns that into a
consistent JSON error body instead of an unhandled exception.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Protocol

#: Coupon payment frequencies (per year) the pricer supports.
ALLOWED_FREQUENCIES: tuple[int, ...] = (1, 2, 4, 12)

#: Upper bound on the number of periods, guarding against absurd ladders.
MAX_PERIODS: int = 1200

#: Tolerance when checking that years x frequency is a whole period count.
_PERIOD_COUNT_TOLERANCE = 1e-9


class BondLike(Protocol):
    """Anything carrying the five raw bond inputs (e.g. ``BondParams``)."""

    face_value: float
    coupon_rate: float
    frequency: int
    years_to_maturity: float
    ytm: float


class BondValidationError(Exception):
    """Raised when bond inputs fail domain validation."""

    def __init__(self, issues: list[dict[str, str]]) -> None:
        self.issues = issues
        summary = "; ".join(f"{i['field']}: {i['issue']}" for i in issues)
        super().__init__(f"invalid bond parameters: {summary}")


@dataclass(frozen=True)
class ValidatedBond:
    """Inputs after validation, plus the derived per-period quantities."""

    face_value: float
    coupon_rate: float
    frequency: int
    years_to_maturity: float
    ytm: float
    periods: int
    per_period_rate: float
    per_period_coupon: float


def validate_bond(params: BondLike) -> ValidatedBond:
    """Validate raw inputs and derive per-period quantities.

    Raises :class:`BondValidationError` listing every problem found, before
    a single cashflow is computed.
    """
    face = params.face_value
    coupon = params.coupon_rate
    freq = params.frequency
    years = params.years_to_maturity
    ytm = params.ytm

    issues: list[dict[str, str]] = []
    if not (math.isfinite(face) and face > 0):
        issues.append({"field": "face_value", "issue": f"must be a positive finite number, got {face!r}"})
    if not (math.isfinite(coupon) and coupon >= 0):
        issues.append({"field": "coupon_rate", "issue": f"must be a non-negative finite decimal, got {coupon!r}"})
    if not (math.isfinite(years) and years > 0):
        issues.append({"field": "years_to_maturity", "issue": f"must be a positive finite number, got {years!r}"})
    if not (isinstance(freq, int) and not isinstance(freq, bool) and freq in ALLOWED_FREQUENCIES):
        issues.append({"field": "frequency", "issue": f"must be one of {ALLOWED_FREQUENCIES}, got {freq!r}"})
    if not math.isfinite(ytm):
        issues.append({"field": "ytm", "issue": f"must be a finite decimal, got {ytm!r}"})
    if issues:
        raise BondValidationError(issues)

    per_period_rate = ytm / freq
    if 1.0 + per_period_rate <= 0:
        raise BondValidationError([{
            "field": "ytm",
            "issue": (
                f"yield too low: 1 + ytm/frequency = 1 + ({ytm})/{freq} = {1.0 + per_period_rate} "
                "must be > 0, otherwise discount factors would be non-positive"
            ),
        }])

    period_count = years * freq
    rounded = round(period_count)
    if abs(period_count - rounded) > _PERIOD_COUNT_TOLERANCE:
        raise BondValidationError([{
            "field": "years_to_maturity",
            "issue": (
                f"years_to_maturity x frequency must be a whole number of periods, "
                f"got {years} x {freq} = {period_count}"
            ),
        }])
    if not 1 <= rounded <= MAX_PERIODS:
        raise BondValidationError([{
            "field": "years_to_maturity",
            "issue": f"implies {rounded} periods, outside the supported range 1..{MAX_PERIODS}",
        }])

    return ValidatedBond(
        face_value=face,
        coupon_rate=coupon,
        frequency=freq,
        years_to_maturity=years,
        ytm=ytm,
        periods=rounded,
        per_period_rate=per_period_rate,
        per_period_coupon=coupon * face / freq,
    )


def validate_yield_shift(shift: float) -> float:
    """Validate the parallel yield shift used by the sensitivity endpoint."""
    if not math.isfinite(shift):
        raise BondValidationError([{
            "field": "yield_shift",
            "issue": f"must be a finite decimal, got {shift!r}",
        }])
    return shift
