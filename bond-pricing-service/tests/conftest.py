"""Shared helpers for the test-suite."""

from __future__ import annotations

from app.models import BondParams
from app.sample import SAMPLE_BOND


def make_params(**overrides) -> BondParams:
    """BondParams based on the sample 5Y par bond, with fields overridden."""
    base = dict(SAMPLE_BOND)
    base.update(overrides)
    return BondParams(**base)
