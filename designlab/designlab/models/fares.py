"""The fare tool's refund rule, in integer cents (Chapter 13).

Amounts never come from a model. This is the deterministic computation
the desk shows beside the model's note: the unflown share of the base
fare by miles, plus the unflown leg's taxes, rounded half up to the cent.
The same inputs give the same cents on every run and every machine.
"""
from __future__ import annotations

from decimal import ROUND_HALF_UP, Decimal


def cents(amount: str) -> int:
    """'1,184.30' -> 118430. Strings in, so no float ever touches money."""
    d = Decimal(amount.replace(",", ""))
    return int((d * 100).to_integral_value(rounding=ROUND_HALF_UP))


def unflown_refund_cents(total_paid: str, taxes: str, flown_miles: int,
                         unflown_miles: int, unflown_taxes: str) -> int:
    if flown_miles < 0 or unflown_miles <= 0:
        raise ValueError("miles must be positive")
    base = cents(total_paid) - cents(taxes)
    if base < 0 or cents(unflown_taxes) > cents(taxes):
        raise ValueError("taxes exceed what was paid")
    share = (Decimal(base) * unflown_miles
             / (flown_miles + unflown_miles))
    return (int(share.to_integral_value(rounding=ROUND_HALF_UP))
            + cents(unflown_taxes))


def usd(c: int) -> str:
    return f"${c // 100:,}.{c % 100:02d}"
