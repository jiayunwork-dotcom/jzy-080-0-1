"""First- and second-order price sensitivity to a parallel yield shift.

Taylor expansion of the dirty price around the current yield y:

    P(y + dy) ~= P * (1 - ModDur * dy)                       first order
    P(y + dy) ~= P * (1 - ModDur * dy + 0.5 * Conv * dy^2)   second order

Both use the *annual* yield shift dy directly, because modified duration
and convexity are expressed in the same annualised convention.
"""

from __future__ import annotations


def first_order_price(price: float, modified_duration: float, yield_shift: float) -> float:
    """Duration-only estimate of the price after a parallel yield shift."""
    return price * (1.0 - modified_duration * yield_shift)


def second_order_price(
    price: float,
    modified_duration: float,
    convexity: float,
    yield_shift: float,
) -> float:
    """Duration-plus-convexity estimate of the price after the shift."""
    return price * (1.0 - modified_duration * yield_shift + 0.5 * convexity * yield_shift**2)
