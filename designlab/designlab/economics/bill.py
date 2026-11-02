"""The provider's invoices for June, July, and August 2026.

The invoice is the provider's usage export summed by identity, the
record nobody at Lakeshore writes. The storm line is priced from the
calls Chapter 37 counted: each billed call carried the 1,800-token
maintenance page in and, because the extraction step's max_tokens was
32,000 and the page made the model write to the limit, 32,000 tokens
out. A timed-out call reports no usage to the client, so the only
record of those tokens is the provider's.

Monthly lines other than the storm are illustrative constants with
the arithmetic shown; the storm is computed.
"""
from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache

from reliability import storm as rs
from serving.prices import Bill

STORM_MAX_TOKENS = 32_000          # extraction step, set in June
SERVICE_RUN_USD = 0.04             # Chapter 35, a servicing run
SERVICE_RUN_TOKENS = 9 * (rs.SERVICE_TOKENS + 320)   # in plus out

# Servicing runs a month: agent attempts, assisted proposals, and the
# conversations that end in no change, from the trace store.
SERVICE_RUNS = {"June": 142_800, "July": 152_520, "August": 204_600}
FARE_WATCH = {"June": 35.20, "July": 57.40, "August": 58.10}
WAIVER_WATCH = {"June": 1.90, "July": 11.30, "August": 391.60}
EVALUATION = {"June": 296.00, "July": 398.00, "August": 344.00}
# Calls that reached the provider with no identity header: a batch
# job sharing an API key in July, found by the nightly reconciler.
NO_IDENTITY = {"June": 0.0, "July": 14.20, "August": 0.0}


def storm_call() -> Bill:
    return Bill(uncached=rs.LOOP_TOKENS, output=STORM_MAX_TOKENS)


@lru_cache(maxsize=None)
def weekend():
    """Chapter 37's storm, minute by minute (seed 37)."""
    return rs.simulate()


def storm_usd() -> float:
    return weekend().billed() * storm_call().usd("small")


def estimate_usd() -> float:
    """INC-6's spend line: the calls priced at their input only."""
    calls = weekend().billed()
    return Bill(uncached=calls * rs.LOOP_TOKENS).usd("small")


@dataclass(frozen=True)
class Line:
    identity: str
    usd: float
    tokens: int


def invoice(month: str) -> list[Line]:
    runs = SERVICE_RUNS[month]
    lines = [
        Line("agent:servicing", runs * SERVICE_RUN_USD,
             runs * SERVICE_RUN_TOKENS),
        Line("loop:fare-watch", FARE_WATCH[month],
             int(FARE_WATCH[month] / 0.40e-6)),
        Line("agent:waiver-watch", WAIVER_WATCH[month],
             int(WAIVER_WATCH[month] / 0.45e-6)),
        Line("eval:harness", EVALUATION[month],
             int(EVALUATION[month] / 2.10e-6)),
    ]
    if NO_IDENTITY[month]:
        lines.append(Line("(no identity)", NO_IDENTITY[month],
                          int(NO_IDENTITY[month] / 0.70e-6)))
    if month == "July":
        calls = weekend().billed()
        lines.insert(3, Line("agent:waiver-watch (Jul 25-26)",
                             storm_usd(),
                             calls * (rs.LOOP_TOKENS +
                                      STORM_MAX_TOKENS)))
    return lines


def total(month: str) -> float:
    return sum(ln.usd for ln in invoice(month))


def per_mtok(month: str) -> float:
    ls = invoice(month)
    return sum(x.usd for x in ls) / sum(x.tokens for x in ls) * 1e6
