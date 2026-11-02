"""Chain checks (Chapter 2).

Two tools:

    find_gaps(design)  -- the gap finder. Given which component writes
                          each state, and which record crosses each gap,
                          name the five gaps and say which are open.
    check_chain(recs)  -- the chain-record checker. Given the six state
                          records of one action, refuse any chain that is
                          out of order, unlinked, or signed by the wrong
                          component (an actor verifying itself, a loop
                          granting itself permission).
"""
from __future__ import annotations

from .states import GAPS, STATES

SHORT = {"output": "output", "proposal": "proposal",
         "permission": "permission", "execution": "execution",
         "verified_outcome": "verified", "business_result": "business"}

# Gaps whose two sides must be written by different components.
INDEPENDENT = {2: "permission lives outside the loop",
               4: "verify with something that did not act"}

# Components that are part of the acting loop.
LOOP = {"model", "agent-loop", "proposal-parser", "rebook-executor",
        "refund-executor"}


def find_gaps(design: dict) -> list[dict]:
    """Return one finding per gap.

    `design` maps each state to a writer and a record, where the
    record names what carries evidence across the gap into that state
    (None when nothing does).
    """
    found = []
    for n, (a, b) in enumerate(GAPS, start=1):
        wa, wb = design[a]["writer"], design[b]["writer"]
        crossing = design[b].get("record")
        if crossing is None:
            status, why = "open", "no record crosses"
        elif n in INDEPENDENT and (wa == wb
                                   or (n == 2 and wb in LOOP)):
            status, why = "open", f"same writer: {wb}"
        else:
            status, why = "closed", crossing
        found.append({"gap": f"G{n}", "pair": (a, b),
                      "status": status, "why": why})
    return found


def summary(found: list[dict]) -> str:
    opened = sum(1 for f in found if f["status"] == "open")
    return f"{len(found)} gaps named, {opened} open"


def check_chain(recs: list, actor: str = "rebook-executor") -> list[str]:
    """Refuse a chain that cannot prove what it claims."""
    problems = []
    states = [r.state for r in recs]
    if tuple(states) != STATES:
        missing = [s for s in STATES if s not in states]
        if missing:
            problems.append("missing: " + ", ".join(missing))
        elif tuple(states) != STATES:
            problems.append("states out of order")
    prev = "genesis"
    for r in recs:
        if r.prev != prev:
            problems.append(f"{SHORT[r.state]}: link broken")
        prev = r.ref
    by = {r.state: r for r in recs}
    p = by.get("permission")
    if p and (p.writer in LOOP or p.body.get("granted_by") in LOOP):
        problems.append(f"G2: permission written by {p.writer}, "
                        "inside the loop")
    v = by.get("verified_outcome")
    e = by.get("execution")
    if v and e and (v.writer == e.writer or
                    v.body.get("verified_by") in (actor, e.writer)):
        problems.append(f"G4: verified outcome written by {v.writer}, "
                        "the actor")
    if v and v.body.get("verdict") != "verified":
        problems.append("G4: outcome not verified")
    if p and e and e.body.get("idempotency_key") != \
            p.body.get("idempotency_key"):
        problems.append("G3: execution key differs from permission key")
    b = by.get("business_result")
    if b and v and b.prev != v.ref:
        problems.append("G5: business result not tied to the outcome")
    return problems


# Designs used in the chapter. Writers and records as drawn on the
# whiteboard on Monday, December 8, 2025, and after the change.
PILOT = {
    "output": {"writer": "model", "record": "model response"},
    "proposal": {"writer": "agent-loop", "record": "tool-call schema"},
    "permission": {"writer": "agent-loop", "record": "tool call itself"},
    "execution": {"writer": "refund-tool", "record": "framework dispatch"},
    "verified_outcome": {"writer": "refund-tool", "record": "status 200"},
    "business_result": {"writer": "ops-dashboard",
                        "record": "turn counted as done"},
}

CHAIN = {
    "output": {"writer": "model", "record": "model response"},
    "proposal": {"writer": "proposal-parser", "record": "typed proposal"},
    "permission": {"writer": "policy-engine", "record": "PRM record"},
    "execution": {"writer": "refund-executor", "record": "keyed call"},
    "verified_outcome": {"writer": "settlement-reconciler",
                         "record": "settlement line"},
    "business_result": {"writer": "scoreboard",
                        "record": "verified-outcome count"},
}

# Second settings, by city and sector.
DISPATCH_SYDNEY = dict(CHAIN, **{
    "proposal": {"writer": "dispatch-agent", "record": "route plan"},
    "permission": {"writer": "dispatch-agent", "record": "self-approval"},
    "execution": {"writer": "fleet-api", "record": "route pushed"},
    "verified_outcome": {"writer": "gps-tracker", "record": "GPS trace"},
})

ENERGY_LEEDS = dict(CHAIN, **{
    "proposal": {"writer": "switch-parser", "record": "tariff request"},
    "permission": {"writer": "pricing-rules", "record": "tariff rule"},
    "execution": {"writer": "switching-agent", "record": "switch call"},
    "verified_outcome": {"writer": "switching-agent",
                         "record": "switch confirmed"},
})

PHARMACY = dict(CHAIN, **{
    "proposal": {"writer": "order-parser", "record": "dispense order"},
    "permission": {"writer": "pharmacist", "record": "sign-off"},
    "execution": {"writer": "dispense-robot", "record": "vial released"},
    "verified_outcome": {"writer": "dispense-robot",
                         "record": "robot count"},
})

DESIGNS = {"pilot": PILOT, "chain": CHAIN, "dispatch": DISPATCH_SYDNEY,
           "energy": ENERGY_LEEDS, "pharmacy": PHARMACY}
