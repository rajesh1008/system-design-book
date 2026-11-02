"""One rebooking through the six states of the evidence chain (Chapter 2).

    output -> proposal -> permission -> execution -> verified outcome
           -> business result

Each state leaves one record, written by a named component, and each
record carries the hash of the record before it. The components are
stand-ins: a parser, a policy engine, an executor that talks to a toy
reservation system, a verifier with its own read-only credential, and a
scoreboard job. Nothing here calls a real airline or processor.
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from typing import Optional

STATES = ("output", "proposal", "permission", "execution",
          "verified_outcome", "business_result")
GAPS = tuple(zip(STATES, STATES[1:]))     # five pairs, G1 to G5

WRITERS = {
    "output": "model",
    "proposal": "proposal-parser",
    "permission": "policy-engine",
    "execution": "rebook-executor",
    "verified_outcome": "pnr-reconciler",
    "business_result": "scoreboard",
}

FLIGHTS = {
    "FLT-000001": {"number": "XMW779", "origin": "ORD", "destination": "BOS",
                   "departs": "2025-12-13T00:00:00Z", "fare_usd": 412.60},
    "FLT-009001": {"number": "XMW781", "origin": "ORD", "destination": "BOS",
                   "departs": "2025-12-12T15:05:00Z", "fare_usd": 431.10},
    "FLT-009002": {"number": "XMW902", "origin": "ORD", "destination": "LGA",
                   "departs": "2025-12-12T14:10:00Z", "fare_usd": 288.00},
}

POLICY = {"policy_id": "rebooking-v1", "max_fare_difference_usd": 150.00,
          "same_route": True, "valid_minutes": 15}


def digest(obj) -> str:
    raw = json.dumps(obj, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(raw.encode()).hexdigest()[:12]


@dataclass
class StateRecord:
    state: str
    writer: str
    body: dict
    prev: str = "genesis"

    def as_dict(self) -> dict:
        return {"state": self.state, "writer": self.writer,
                "prev": self.prev, "body": self.body}

    @property
    def ref(self) -> str:
        return digest(self.as_dict())


@dataclass
class Reservations:
    """A toy reservation system: the record of fact for bookings.

    `slow_calls` are applied but answered after the caller's timeout.
    Writes need the executor credential; reads need the reader one.
    """
    segments: dict = field(default_factory=lambda: {
        "LTG-4471902": ["FLT-000001"]})
    slow_calls: set = field(default_factory=set)
    honor_keys: bool = True
    calls: int = 0
    tickets: list = field(default_factory=list)
    _by_key: dict = field(default_factory=dict)

    def rebook(self, credential: str, itinerary: str, old: str, new: str,
               key: Optional[str]) -> dict:
        if credential != "cred:rebook-executor":
            raise PermissionError("write needs the executor credential")
        self.calls += 1
        if self.honor_keys and key and key in self._by_key:
            return dict(self._by_key[key], replayed=True)
        segs = self.segments[itinerary]
        if old in segs:
            segs[segs.index(old)] = new
        ticket = f"TKT-{len(self.tickets) + 1:05d}"
        self.tickets.append({"ticket": ticket, "itinerary": itinerary,
                             "flight": new, "key": key})
        result = {"status": "ticketed", "ticket": ticket}
        if key:
            self._by_key[key] = result
        if self.calls in self.slow_calls:
            raise TimeoutError("no answer within 8.0 s")
        return result

    def read(self, credential: str, itinerary: str) -> dict:
        if credential != "cred:pnr-reader":
            raise PermissionError("read needs the reader credential")
        return {"segments": list(self.segments[itinerary]),
                "tickets": [t for t in self.tickets
                            if t["itinerary"] == itinerary]}


def to_proposal(text: str, itinerary: str, held: list[str]) -> tuple:
    """Gap one: turn model output into a typed proposal, or refuse it."""
    start, end = text.find("{"), text.rfind("}")
    if start < 0 or end < start:
        return None, ["no JSON object in output"]
    try:
        raw = json.loads(text[start:end + 1])
    except json.JSONDecodeError as e:
        return None, [f"unparseable output: {e.msg}"]
    problems = []
    if raw.get("action") != "rebook":
        problems.append(f"unknown action {raw.get('action')!r}")
    if raw.get("itinerary") != itinerary:
        problems.append("itinerary does not match the contact")
    old, new = raw.get("from_flight"), raw.get("to_flight")
    if old not in held:
        problems.append(f"{old} is not on the itinerary")
    if new not in FLIGHTS:
        problems.append(f"{new} is not a known flight")
    if problems:
        return None, problems
    diff = round(FLIGHTS[new]["fare_usd"] - FLIGHTS[old]["fare_usd"], 2)
    return {"action": "rebook", "itinerary": itinerary, "from_flight": old,
            "to_flight": new, "fare_difference_usd": diff,
            "reason": str(raw.get("reason", ""))[:200]}, []


def grant(proposal: dict, proposal_ref: str, now: str) -> tuple:
    """Gap two: the policy engine decides, outside the loop."""
    old = FLIGHTS[proposal["from_flight"]]
    new = FLIGHTS[proposal["to_flight"]]
    problems = []
    if (old["origin"], old["destination"]) != (new["origin"],
                                               new["destination"]):
        problems.append("route differs from the booked route")
    if proposal["fare_difference_usd"] > POLICY["max_fare_difference_usd"]:
        problems.append("fare difference above the policy limit")
    if problems:
        return None, problems
    perm = {"permission_id": "PRM-20932", "granted_by": "policy-engine",
            "policy_version": POLICY["policy_id"], "bound_to": proposal_ref,
            "max_fare_difference_usd": POLICY["max_fare_difference_usd"],
            "issued_at": now, "valid_minutes": POLICY["valid_minutes"],
            "single_use": True}
    perm["idempotency_key"] = "idem-" + digest([proposal_ref, perm])
    return perm, []


def permits(perm: dict, proposal_ref: str, used: set) -> list[str]:
    """Gap three: is this permission live, bound to this proposal, unused?"""
    problems = []
    if perm.get("granted_by") != "policy-engine":
        problems.append("permission not from the policy engine")
    if perm.get("bound_to") != proposal_ref:
        problems.append("permission bound to a different proposal")
    if perm.get("permission_id") in used:
        problems.append("single-use permission already spent")
    return problems


def execute(res: Reservations, proposal: dict, perm: dict,
            max_attempts: int = 3) -> dict:
    """Act inside the permission, under its key; retries reuse the key."""
    attempts = []
    for n in range(1, max_attempts + 1):
        try:
            out = res.rebook("cred:rebook-executor", proposal["itinerary"],
                             proposal["from_flight"], proposal["to_flight"],
                             perm["idempotency_key"])
            attempts.append({"n": n, "result": "answered",
                             "replayed": bool(out.get("replayed"))})
            return {"permission_id": perm["permission_id"],
                    "idempotency_key": perm["idempotency_key"],
                    "attempts": attempts, "reported": out["status"],
                    "ticket": out["ticket"]}
        except TimeoutError:
            attempts.append({"n": n, "result": "timeout after 8.0 s"})
    return {"permission_id": perm["permission_id"],
            "idempotency_key": perm["idempotency_key"],
            "attempts": attempts, "reported": "unknown", "ticket": None}


def verify(res: Reservations, proposal: dict, execution: dict,
           verifier: str = "pnr-reconciler") -> dict:
    """Gap four: read the record of fact, read-only."""
    seen = res.read("cred:pnr-reader", proposal["itinerary"])
    keyed = [t for t in seen["tickets"]
             if t["key"] == execution["idempotency_key"]]
    holds_new = proposal["to_flight"] in seen["segments"]
    dropped_old = proposal["from_flight"] not in seen["segments"]
    ok = holds_new and dropped_old and len(keyed) == 1
    return {"verified_by": verifier, "source": "reservation record",
            "tickets_for_key": len(keyed), "holds_new": holds_new,
            "released_old": dropped_old,
            "verdict": "verified" if ok else "not verified"}


def business_result(verified: dict, contact: dict, cost_usd: float) -> dict:
    """Gap five: tie the verified outcome to what the business counts."""
    done = verified["verdict"] == "verified"
    return {"contact_id": contact["contact_id"],
            "counts_as": "verified change" if done else "open case",
            "handled_by": "agent", "person_minutes": 0,
            "cost_usd": cost_usd, "kept_booking": done,
            "repeat_contact_check": "after 7 days, from contacts table"}


def run_rebooking(output_text: str, res: Optional[Reservations] = None,
                  now: str = "2025-12-18T15:02:11Z",
                  forge: Optional[str] = None) -> tuple:
    """Run one rebooking through all six states.

    `forge` injects a failure: "self_verify" has the executor sign the
    verified outcome; "self_permit" has the parser write the permission.
    Returns (records, refusal). A refusal stops the chain where it fails.
    """
    res = res or Reservations(slow_calls={1})
    itin, held = "LTG-4471902", ["FLT-000001"]
    recs: list[StateRecord] = []

    def add(state: str, body: dict, writer: Optional[str] = None):
        prev = recs[-1].ref if recs else "genesis"
        who = writer or WRITERS[state]
        recs.append(StateRecord(state, who, body, prev))

    add("output", {"model": "small", "text_sha": digest(output_text),
                   "contact_id": "CON-0013311"})
    prop, why = to_proposal(output_text, itin, held)
    if prop is None:
        return recs, ("G1", why)
    add("proposal", prop)
    perm, why = grant(prop, recs[-1].ref, now)
    if perm is None:
        return recs, ("G2", why)
    add("permission", perm,
        writer="proposal-parser" if forge == "self_permit" else None)
    why = permits(perm, recs[-2].ref, used=set())
    if why:
        return recs, ("G3", why)
    ex = execute(res, prop, perm)
    add("execution", ex)
    signer = "rebook-executor" if forge == "self_verify" else None
    checker = signer or WRITERS["verified_outcome"]
    v = verify(res, prop, ex, verifier=checker)
    add("verified_outcome", v, writer=signer)
    contact = {"contact_id": "CON-0013311"}
    add("business_result", business_result(v, contact, cost_usd=0.41))
    return recs, None
