"""Chargeback: who pays for what the provider billed.

Under finance's May rule the invoice went to the servicing agent's
owner, customer operations, because the only spend with a task id was
servicing's and the pool without one was split across the servicing
paths. DR-38.1 charges by identity: every call carries the caller's
identity at the gateway, every identity has an owner, an incident's
spend is a line on the owner's statement, and spend with no identity
is shown as unallocated, never spread to whoever is largest.

The shared platform (gateway, trace store, trail; Chapter 18's $2,400
a month fixed) is split by each owner's ordinary model spend, in
cents, by largest remainder, so the statement adds to the invoice.
An owner with no ordinary spend gets none of it.
"""
from __future__ import annotations

from cost.unit import attribute
from corpus.traces import KINDS

from . import bill

PLATFORM_FIXED = 2_400.00
OWNERS = {
    "agent:servicing": "customer operations",
    "loop:fare-watch": "platform engineering",
    "agent:waiver-watch": "platform engineering",
    "eval:harness": "applied research",
}
INCIDENT = {"agent:waiver-watch (Jul 25-26)": "INC-6"}


def _owner(identity: str, rule: str) -> str:
    if rule == "pool":
        # May rule: task spend to its path, the rest pooled over the
        # servicing paths, so all of it lands on customer operations
        return "customer operations"
    if identity in INCIDENT:
        return "platform engineering"
    return OWNERS.get(identity, "unallocated")


def statement(month: str, rule: str = "identity") -> dict[str, dict]:
    out: dict[str, dict] = {}
    for ln in bill.invoice(month):
        o = _owner(ln.identity, rule)
        row = out.setdefault(o, {"model": 0.0, "incident": 0.0,
                                 "platform": 0.0})
        row["incident" if ln.identity in INCIDENT and rule != "pool"
            else "model"] += ln.usd
    weights = {o: r["model"] for o, r in out.items()
               if o != "unallocated"}
    cents = attribute(round(PLATFORM_FIXED * 100), weights)
    for o, c in cents.items():
        out[o]["platform"] = c / 100
    for r in out.values():
        r["total"] = r["model"] + r["incident"] + r["platform"]
    return out


def by_use_case(month: str) -> dict[str, float]:
    """Customer operations' model spend split by kind of change, in
    cents by largest remainder, using each kind's share of changes."""
    servicing = next(ln for ln in bill.invoice(month)
                     if ln.identity == "agent:servicing")
    cents = attribute(round(servicing.usd * 100), dict(KINDS))
    return {k: c / 100 for k, c in cents.items()}
