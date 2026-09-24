"""Pydantic schemas for the HTTP boundary.

These models only carry data and light type coercion; all domain checks
live in :mod:`app.validation` so every endpoint validates identically
before any computation runs.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class BondParams(BaseModel):
    """Raw pricing inputs for a fixed-rate bullet bond.

    Rates are annual decimals (0.05 means 5%).
    """

    model_config = ConfigDict(extra="forbid")

    face_value: float = Field(..., description="Par/face amount; must be > 0")
    coupon_rate: float = Field(..., description="Annual coupon rate as a decimal; >= 0")
    frequency: int = Field(..., description="Coupon payments per year: 1, 2, 4 or 12")
    years_to_maturity: float = Field(..., description="Years left to maturity; > 0")
    ytm: float = Field(..., description="Annual yield to maturity as a decimal")


class SensitivityRequest(BondParams):
    """Bond inputs plus the parallel shift applied to the annual yield."""

    yield_shift: float = Field(
        ...,
        description="Parallel shift of the annual YTM as a decimal (0.01 = +100bp)",
    )


class CashflowPV(BaseModel):
    period: int
    time_years: float
    cashflow: float
    discount_factor: float
    present_value: float


class PriceResponse(BaseModel):
    input: BondParams
    periods: int
    per_period_rate: float
    dirty_price: float
    cashflows: list[CashflowPV]


class RiskResponse(BaseModel):
    input: BondParams
    periods: int
    per_period_rate: float
    dirty_price: float
    macaulay_duration: float
    modified_duration: float
    convexity: float


class SensitivityResponse(BaseModel):
    input: BondParams
    yield_shift: float
    shifted_ytm: float
    base_dirty_price: float
    modified_duration: float
    convexity: float
    first_order_estimate: float
    second_order_estimate: float
    exact_reprice: float
    first_order_error: float
    second_order_error: float


class ErrorDetail(BaseModel):
    field: str
    issue: str


class ErrorBody(BaseModel):
    code: str
    message: str
    details: list[ErrorDetail]


class ErrorResponse(BaseModel):
    """Structured error envelope returned for every rejected request."""

    error: ErrorBody
