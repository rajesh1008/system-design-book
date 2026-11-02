"""The June 26 fix as policy: destination-v1 in a signed bundle.

The rule says where a refund may go: only to a form of payment that
paid for the booking. It is data in the bundle, so its digest is in
every decision line, and it was evaluated in shadow before it was
active. The policy engine of Chapter 31 has a fixed set of rule types;
the lab evaluates this one beside the engine, in `case.destination_v1`,
rather than change the engine's code.
"""
from __future__ import annotations

from common.clock import FixedClock
from policy.bundle import BundleError, BundleStore
from policy.rules import AUTHOR, BUNDLES, SIGNER

RULE = {"id": "refund-destination", "policy": "destination-v1",
        "type": "destination", "tools": ["refund_ticket"],
        "field": "refund_to", "allow": "forms_that_paid",
        "route": "payments desk"}
OLD = "pb-2026.06.22"
NEW = "pb-2026.06.22.2"
SHADOW_MIN = 30


def lifecycle(shadow_minutes: int = 41) -> tuple[list[str], BundleStore]:
    """June 26: propose, the author tries to sign, Rachel signs, shadow,
    then active once the shadow has run at least SHADOW_MIN minutes."""
    clock = FixedClock("2026-06-26T13:05:00-05:00", step_seconds=0)
    store = BundleStore(clock)
    store.propose(OLD, BUNDLES[OLD], AUTHOR)
    store.sign(OLD, SIGNER)
    store.move(OLD, "shadow", AUTHOR)
    store.move(OLD, "active", AUTHOR)
    log = []
    clock.advance(26 * 60)
    b = store.propose(NEW, [RULE] + BUNDLES[OLD], AUTHOR)
    log.append(f"proposed {NEW} digest {b.digest} by {AUTHOR}")
    try:
        store.sign(NEW, AUTHOR)
    except BundleError as e:
        log.append(f"refused: {e}")
    store.sign(NEW, SIGNER)
    log.append(f"signed by {SIGNER}")
    store.move(NEW, "shadow", AUTHOR)
    start = clock.now()
    log.append(f"shadow from {start.strftime('%H:%M')}")
    clock.advance(shadow_minutes * 60)
    if shadow_minutes < SHADOW_MIN:
        log.append(f"not activated: shadow {shadow_minutes} min "
                   f"< {SHADOW_MIN}")
        return log, store
    store.move(NEW, "active", AUTHOR)
    log.append(f"active at {clock.now().strftime('%H:%M')} after "
               f"{shadow_minutes} min; {OLD} superseded")
    return log, store


def replay_month(lines: list[str]) -> tuple[int, list[str]]:
    """Shadow evidence over the past: run destination-v1 on every June
    proposal in the trail. It refuses only those whose refund_to is not
    a form that paid for the run's booking."""
    import json
    paid: dict[str, list[str]] = {}
    seen, refused = 0, []
    for line in lines:
        e = json.loads(line)
        if e["event"] == "run":
            paid[e["run"]] = e.get("forms_paid", [])
        elif e["event"] == "proposal":
            seen += 1
            dest = e.get("refund_to")
            if dest and dest not in paid.get(e["run"], []):
                refused.append(e["proposal"])
    return seen, refused
