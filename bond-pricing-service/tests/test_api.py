"""End-to-end HTTP behaviour, including the sample bond and concurrency."""

from __future__ import annotations

import asyncio

import httpx
import pytest
from fastapi.testclient import TestClient

from app import engine
from app.main import app
from app.models import BondParams
from app.sample import SAMPLE_BOND

client = TestClient(app)


def test_health():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_sample_bond_is_a_five_year_par_bond():
    data = client.get("/sample-bond").json()
    assert data["years_to_maturity"] == 5.0
    assert data["coupon_rate"] == data["ytm"]  # par bond


def test_sample_bond_reproduces_par_relation_through_the_api():
    sample = client.get("/sample-bond").json()
    priced = client.post("/price", json=sample).json()
    assert priced["dirty_price"] == pytest.approx(sample["face_value"], rel=1e-9)


def test_price_endpoint_returns_per_period_detail():
    data = client.post("/price", json=SAMPLE_BOND).json()
    assert data["periods"] == 10
    assert len(data["cashflows"]) == 10
    first = data["cashflows"][0]
    assert {"period", "time_years", "cashflow", "discount_factor", "present_value"} <= set(first)
    total = sum(cf["present_value"] for cf in data["cashflows"])
    assert data["dirty_price"] == pytest.approx(total, rel=1e-12)


def test_risk_endpoint_returns_three_measures():
    data = client.post("/risk", json=SAMPLE_BOND).json()
    assert data["macaulay_duration"] == pytest.approx(4.485433, abs=1e-4)
    assert data["modified_duration"] == pytest.approx(4.376032, abs=1e-4)
    assert data["convexity"] == pytest.approx(22.612322, abs=1e-4)
    assert data["dirty_price"] == pytest.approx(SAMPLE_BOND["face_value"], rel=1e-9)


def test_sensitivity_endpoint_compares_three_prices():
    data = client.post("/sensitivity", json={**SAMPLE_BOND, "yield_shift": 0.01}).json()
    assert data["first_order_estimate"] < data["exact_reprice"]
    assert data["second_order_estimate"] > data["first_order_estimate"]
    assert abs(data["second_order_error"]) < abs(data["first_order_error"])


def test_concurrent_requests_are_isolated():
    """Many simultaneous requests with distinct inputs must each get their
    own correct answer — no shared intermediate state between requests."""
    payloads = [
        {
            **SAMPLE_BOND,
            "coupon_rate": 0.01 + 0.004 * i,
            "ytm": 0.02 + 0.005 * i,
            "years_to_maturity": float(i),
        }
        for i in range(1, 25)
    ]

    async def fire_all():
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as ac:
            return await asyncio.gather(*(ac.post("/risk", json=p) for p in payloads))

    responses = asyncio.run(fire_all())

    for payload, response in zip(payloads, responses):
        assert response.status_code == 200
        expected = engine.risk_metrics(BondParams(**payload))
        got = response.json()
        assert got["dirty_price"] == pytest.approx(expected["dirty_price"], rel=1e-12)
        assert got["macaulay_duration"] == pytest.approx(expected["macaulay_duration"], rel=1e-12)
        assert got["convexity"] == pytest.approx(expected["convexity"], rel=1e-12)
