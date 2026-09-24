"""HTTP interface: FastAPI application exposing the pricing engine.

Only JSON over HTTP — no pages, no accounts, no positions. The engine is
stateless, so concurrent requests are fully isolated from one another.
"""

from __future__ import annotations

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from . import engine, sample
from .models import (
    BondParams,
    ErrorResponse,
    PriceResponse,
    RiskResponse,
    SensitivityRequest,
    SensitivityResponse,
)
from .validation import BondValidationError

app = FastAPI(
    title="Bond Pricing & Rate Risk Engine",
    version="1.0.0",
    description=(
        "Fixed-rate bullet bond valuation: dirty price with per-period "
        "present values, Macaulay/modified duration, convexity, and "
        "first/second-order yield-shift sensitivity versus exact repricing."
    ),
)


def _error_payload(code: str, message: str, details: list[dict]) -> dict:
    return {"error": {"code": code, "message": message, "details": details}}


@app.exception_handler(BondValidationError)
async def bond_validation_handler(_: Request, exc: BondValidationError) -> JSONResponse:
    """Domain validation failures -> structured 422, never a stack trace."""
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content=_error_payload("INVALID_BOND_PARAMETERS", str(exc), exc.issues),
    )


@app.exception_handler(RequestValidationError)
async def request_validation_handler(_: Request, exc: RequestValidationError) -> JSONResponse:
    """Malformed payloads (missing/wrong-typed fields) -> structured 422."""
    details = [
        {"field": ".".join(str(part) for part in err.get("loc", ())), "issue": err.get("msg", "")}
        for err in exc.errors()
    ]
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content=_error_payload("MALFORMED_REQUEST", "request body failed schema validation", details),
    )


@app.get("/health", tags=["meta"])
def health() -> dict:
    return {"status": "ok"}


@app.get("/sample-bond", response_model=BondParams, tags=["meta"])
def sample_bond() -> dict:
    """Built-in 5-year par bond for manual verification of the conventions."""
    return sample.SAMPLE_BOND


@app.post(
    "/price",
    response_model=PriceResponse,
    responses={422: {"model": ErrorResponse}},
    tags=["pricing"],
)
def price(params: BondParams) -> dict:
    """Dirty price plus the per-period present-value breakdown."""
    return engine.price_bond(params)


@app.post(
    "/risk",
    response_model=RiskResponse,
    responses={422: {"model": ErrorResponse}},
    tags=["pricing"],
)
def risk(params: BondParams) -> dict:
    """Macaulay duration, modified duration and convexity."""
    return engine.risk_metrics(params)


@app.post(
    "/sensitivity",
    response_model=SensitivityResponse,
    responses={422: {"model": ErrorResponse}},
    tags=["pricing"],
)
def sensitivity(request: SensitivityRequest) -> dict:
    """First-order, second-order and exact-repriced prices after a yield shift."""
    return engine.sensitivity_analysis(request, request.yield_shift)
