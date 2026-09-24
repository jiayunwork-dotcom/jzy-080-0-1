"""Input validation: illegal combinations are rejected with structured
errors before any computation, on every endpoint."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.sample import SAMPLE_BOND

client = TestClient(app)

SENSITIVITY_PAYLOAD = {**SAMPLE_BOND, "yield_shift": 0.01}


def _post(endpoint: str, payload: dict):
    return client.post(endpoint, json=payload)


def _assert_structured_error(response, field: str | None = None):
    assert response.status_code == 422
    body = response.json()
    assert set(body) == {"error"}
    error = body["error"]
    assert error["code"] == "INVALID_BOND_PARAMETERS"
    assert error["message"]
    assert isinstance(error["details"], list) and error["details"]
    if field is not None:
        assert any(d["field"] == field for d in error["details"])


@pytest.mark.parametrize("endpoint,payload", [
    ("/price", SAMPLE_BOND),
    ("/risk", SAMPLE_BOND),
    ("/sensitivity", SENSITIVITY_PAYLOAD),
])
@pytest.mark.parametrize("field,value", [
    ("face_value", 0.0),
    ("face_value", -1000.0),
    ("years_to_maturity", 0.0),
    ("years_to_maturity", -5.0),
    ("coupon_rate", -0.01),
])
def test_illegal_inputs_rejected_on_every_endpoint(endpoint, payload, field, value):
    response = _post(endpoint, {**payload, field: value})
    _assert_structured_error(response, field)


def test_yield_making_discount_factor_zero_is_rejected():
    # 1 + ytm/frequency == 0 exactly: discount factors would be undefined.
    response = _post("/price", {**SAMPLE_BOND, "ytm": -2.0})
    _assert_structured_error(response, "ytm")


def test_yield_making_discount_factor_negative_is_rejected():
    # 1 + ytm/frequency < 0: odd-period discount factors would be negative.
    response = _post("/price", {**SAMPLE_BOND, "ytm": -2.5})
    _assert_structured_error(response, "ytm")


def test_shifted_yield_making_discount_factor_non_positive_is_rejected():
    response = _post("/sensitivity", {**SAMPLE_BOND, "yield_shift": -3.0})
    _assert_structured_error(response, "ytm")


def test_non_integer_period_count_is_rejected():
    response = _post("/price", {**SAMPLE_BOND, "years_to_maturity": 5.3, "frequency": 2})
    _assert_structured_error(response, "years_to_maturity")


def test_unsupported_frequency_is_rejected():
    response = _post("/price", {**SAMPLE_BOND, "frequency": 3})
    _assert_structured_error(response, "frequency")


def test_excessive_period_count_is_rejected():
    response = _post("/price", {**SAMPLE_BOND, "years_to_maturity": 500.0, "frequency": 12})
    _assert_structured_error(response, "years_to_maturity")


def test_missing_field_is_a_structured_error_not_a_crash():
    payload = {k: v for k, v in SAMPLE_BOND.items() if k != "ytm"}
    response = _post("/price", payload)
    assert response.status_code == 422
    body = response.json()
    assert body["error"]["code"] == "MALFORMED_REQUEST"
    assert any("ytm" in d["field"] for d in body["error"]["details"])


def test_wrong_type_is_a_structured_error():
    response = _post("/price", {**SAMPLE_BOND, "face_value": "one thousand"})
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "MALFORMED_REQUEST"


def test_non_finite_yield_shift_is_rejected():
    response = _post("/sensitivity", {**SAMPLE_BOND, "yield_shift": "NaN"})
    assert response.status_code == 422
    assert response.json()["error"]["code"] in {"MALFORMED_REQUEST", "INVALID_BOND_PARAMETERS"}


def test_error_body_shape_is_stable():
    response = _post("/price", {**SAMPLE_BOND, "face_value": -1.0})
    error = response.json()["error"]
    assert {"code", "message", "details"} <= set(error)
    detail = error["details"][0]
    assert {"field", "issue"} <= set(detail)
