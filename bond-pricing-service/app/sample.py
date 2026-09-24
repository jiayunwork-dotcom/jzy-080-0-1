"""Built-in sample bond used for manual verification of the conventions.

A 5-year par bond: coupon rate equals yield to maturity, so the dirty
price must come out exactly at face value, and its duration/convexity
can be checked by hand (see README.md for the worked numbers).
"""

from __future__ import annotations

SAMPLE_BOND: dict = {
    "face_value": 1000.0,
    "coupon_rate": 0.05,
    "frequency": 2,
    "years_to_maturity": 5.0,
    "ytm": 0.05,
}
