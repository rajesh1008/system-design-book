"""Retry policies by plane (Chapter 12).

A retry is safe only when the operation is a read, or when the effect
carries a key the supplier honors, minted once before the first
attempt. Each plane gets its own timeout and its own budget, and the
system retries at one layer only: three attempts at each of five
layers is 3**5 = 243 calls for one request.
"""
from __future__ import annotations

import random
from dataclasses import dataclass


@dataclass(frozen=True)
class RetryPolicy:
    plane: str
    operation: str
    timeout_s: float
    attempts: int
    base_s: float
    cap_s: float
    key: str          # "read", "ledger key", or "never"


POLICIES = (
    RetryPolicy("action", "model call", 30.0, 2, 1.0, 4.0, "read"),
    RetryPolicy("action", "tool read", 5.0, 3, 0.2, 2.0, "read"),
    RetryPolicy("action", "effect, native key", 8.0, 3, 1.0, 8.0,
                "ledger key"),
    RetryPolicy("action", "effect, lookup", 8.0, 2, 5.0, 30.0,
                "ledger key"),
    RetryPolicy("action", "effect, no key", 8.0, 1, 0.0, 0.0, "never"),
    RetryPolicy("control", "policy decision", 2.0, 2, 0.1, 0.5, "read"),
    RetryPolicy("control", "approval wait", 120.0, 1, 0.0, 0.0, "never"),
    RetryPolicy("knowledge", "fact fetch", 3.0, 2, 0.2, 1.0, "read"),
    RetryPolicy("trail", "record write", 2.0, 5, 0.1, 5.0,
                "ledger key"),
)


def policy(operation: str) -> RetryPolicy:
    return next(p for p in POLICIES if p.operation == operation)


def amplification(layers: int, attempts: int) -> int:
    """Calls at the bottom for one request at the top."""
    return attempts ** layers


def backoff(attempt: int, base: float, cap: float,
            rng: random.Random) -> float:
    """Capped exponential backoff with full jitter."""
    return rng.uniform(0.0, min(cap, base * 2 ** (attempt - 1)))


class RetryBudget:
    """A token bucket: each retry spends a token, each success refills
    a tenth of one. When the bucket is empty, the caller does not
    retry, and a slow supplier is not hit harder."""

    def __init__(self, size: float = 10.0, refill: float = 0.1):
        self.size, self.refill, self.tokens = size, refill, size

    def success(self) -> None:
        self.tokens = min(self.size, self.tokens + self.refill)

    def may_retry(self) -> bool:
        if self.tokens >= 1.0:
            self.tokens -= 1.0
            return True
        return False
