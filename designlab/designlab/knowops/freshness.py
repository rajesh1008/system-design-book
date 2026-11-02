"""Freshness as a contract: for each source, who owns the truth, how
old a read may be when it is used, which clock measures the age, and
what happens when the read is too old or the answer is unknown.

Freshness is not the same as being in effect (Chapter 19): a page read
three minutes ago can still be the wrong version. The contract covers
age; the as-of filter covers validity. Both apply.
"""
from __future__ import annotations

from dataclasses import dataclass

MIN, HOUR, DAY = 60, 3600, 86400


@dataclass(frozen=True)
class Contract:
    source: str
    record: str              # who owns the truth
    max_age_s: int | None    # oldest read that may be used
    clock: str               # what the age is measured from
    on_stale: str            # what the agent does instead
    owner: str
    event_max_age_s: int | None = None   # tighter during an event


CONTRACTS = (
    Contract("booking record", "booking system", 15 * MIN,
             "read time", "re-read before any effect; unknown raises",
             "Daniel Price"),
    Contract("flight status", "carrier schedule feed", 5 * MIN,
             "feed event time", "hold the proposal and re-read",
             "Ben Carter"),
    Contract("fare rules", "carrier rule pages", DAY,
             "index time", "send the proposal to a person",
             "Dr. Hannah Clarke"),
    Contract("waivers and notices", "carrier notice pages", DAY,
             "index time", "send the proposal to a person",
             "Dr. Hannah Clarke", event_max_age_s=15 * MIN),
    Contract("help articles", "Lakeshore help center", 7 * DAY,
             "index time", "answer with a link, not a quote",
             "Marcus Bell"),
    Contract("supplier terms", "supplier contracts", 7 * DAY,
             "index time", "send the proposal to a person",
             "Rachel Morgan"),
    Contract("customer memory", "the customer, via the record",
             None, "observed time; TTL by type",
             "evidence only; a record field supersedes it",
             "Daniel Price"),
)


def contract_for(source: str) -> Contract:
    for c in CONTRACTS:
        if c.source == source:
            return c
    raise KeyError(source)


def check(source: str, age_s: float | None,
          event_active: bool = False) -> str:
    """'fresh', 'stale', or 'unknown' for one read of one source."""
    c = contract_for(source)
    if age_s is None:
        return "unknown"
    limit = c.max_age_s
    if event_active and c.event_max_age_s is not None:
        limit = c.event_max_age_s
    if limit is None:
        return "fresh"           # memory: governed by TTL, not age
    return "fresh" if age_s <= limit else "stale"
