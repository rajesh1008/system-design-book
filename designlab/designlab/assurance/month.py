"""A month of refunds on the trail: the lab's model of June 2026.

Every refund run writes the evidence chain of Chapter 2 as trail lines:
the run (with its release and the AI notice the customer saw), the
proposal, the policy decision, the person's approval, the execution,
the ledger's verification, and the notice. Changes write their own
lines: releases, bundles, tool schemas, and findings. The counts follow
Chapter 34's June: 6,001 refund runs, 99 approver edits, 33 hand-offs
after a tool error, and one rejection, on June 24. Every identifier,
card reference, and amount is synthetic; no card number is written.
Lakeshore figures are illustrative.
"""
from __future__ import annotations

import hashlib
import json
from datetime import datetime, timedelta

from common.rand import seeded
from common.trail import TrailWriter
from threats.email import vault_ref

from . import case

RUNS = 6001
EDITS = 99
HANDOFFS = 33
APPROVERS = ("Teresa Alvarez", "approver A-02", "approver A-03",
             "approver A-04")
DAY0 = datetime.fromisoformat("2026-06-01T00:00:00-05:00")
# What changed in June, in the order it happened (Chapters 31 to 34).
CHANGES = (
    ("2026-06-02T09:00:00-05:00", "release", "R-0602 memory"),
    ("2026-06-03T09:00:00-05:00", "release", "R-0603 model"),
    ("2026-06-05T09:00:00-05:00", "release", "R-0605 context"),
    ("2026-06-08T09:00:00-05:00", "bundle", "pb-2026.06.08 active"),
    ("2026-06-12T15:00:00-05:00", "release", "R-0612 tool server"),
    ("2026-06-12T15:00:00-05:00", "schema",
     "refund_ticket 3.1 adds refund_to"),
    ("2026-06-15T09:00:00-05:00", "bundle", "pb-2026.06.15 active"),
    ("2026-06-19T09:00:00-05:00", "release", "R-0619 tool server"),
    ("2026-06-21T09:00:00-05:00", "release", "R-0621 identity"),
    ("2026-06-22T09:00:00-05:00", "bundle", "pb-2026.06.22 active"),
    ("2026-06-23T09:00:00-05:00", "release", "R-0623 knowledge"),
    ("2026-06-24T09:40:00-05:00", "finding", "F-0624-01 opened"),
    ("2026-06-26T14:12:00-05:00", "bundle", "pb-2026.06.22.2 active"),
    ("2026-06-26T14:30:00-05:00", "check", "card-on-file v2 live"),
)
FIX_AT = "2026-06-26T14:12:00-05:00"
SIGNER = "Rachel Morgan"


class SetClock:
    def __init__(self):
        self.t = DAY0

    def now(self) -> datetime:
        return self.t


def digest(args: dict) -> str:
    raw = json.dumps(args, sort_keys=True).encode()
    return hashlib.sha256(raw).hexdigest()[:16]


def release_on(at: str) -> str:
    rel = "before R-0602"
    for when, kind, what in CHANGES:
        if kind == "release" and when <= at:
            rel = what.split()[0]
    return rel


def bundle_on(at: str) -> str:
    b = "before pb-2026.06.08"
    for when, kind, what in CHANGES:
        if kind == "bundle" and when <= at:
            b = what.split()[0]
    return b


def build(runs: int = RUNS, seed: int = 36) -> TrailWriter:
    rng = seeded(seed, "june")
    clock = SetClock()
    tw = TrailWriter(clock=clock)
    times = sorted(rng.randrange(0, 30 * 86400 - 3600)
                   for _ in range(runs))
    target = 23 * 86400 + 8 * 3600 + 29 * 60 + 40   # 08:29:40, June 24
    hotel = min(range(runs), key=lambda i: abs(times[i] - target))
    times[hotel] = target
    edits = set(rng.sample([i for i in range(runs) if i != hotel],
                           EDITS))
    rest = [i for i in range(runs) if i != hotel and i not in edits]
    handoffs = set(rng.sample(rest, HANDOFFS))
    changes = [(datetime.fromisoformat(w), k, x) for w, k, x in CHANGES]
    ci = 0
    for i, t in enumerate(times):
        at = max(DAY0 + timedelta(seconds=t), clock.t)
        while ci < len(changes) and changes[ci][0] <= at:
            clock.t = max(changes[ci][0], clock.t)
            tw.append({"event": "change", "kind": changes[ci][1],
                       "what": changes[ci][2]})
            ci += 1
        clock.t = at
        _run(tw, clock, rng, i, at, i == hotel, i in edits,
             i in handoffs)
    while ci < len(changes):
        clock.t = changes[ci][0]
        tw.append({"event": "change", "kind": changes[ci][1],
                   "what": changes[ci][2]})
        ci += 1
    return tw


def _run(tw, clock, rng, i, at, hotel, edit, handoff) -> None:
    iso = at.isoformat()
    run = f"run-06{at.day:02d}-{i + 1:05d}"
    ref = case.BOOKING if hotel else f"LTG-{5600000 + i:07d}"
    paid = case.PAID_REF if hotel else \
        vault_ref(f"4000{rng.randrange(10 ** 12):012d}")
    forms = [paid] + ([f"credit-{i:05d}"] if edit else [])
    amount = case.AMOUNT if hotel else \
        f"{rng.randrange(8000, 120000) / 100:.2f}"
    rel = release_on(iso)
    tw.append({"event": "run", "run": run, "booking": ref,
               "release": rel, "ai_notice": "shown",
               "forms_paid": forms})
    if handoff:
        _tick(clock, 4)
        tw.append({"event": "handoff", "run": run,
                   "why": "tool error after retries"})
        return
    pid = "P-0624-HOTEL" if hotel else f"P-{i + 1:05d}"
    dest = case.ATTACK_REF if hotel else paid
    args = {"booking": ref, "amount_usd": amount, "refund_to": dest}
    _tick(clock, 6)
    tw.append({"event": "proposal", "run": run, "proposal": pid,
               "tool": "refund_ticket", "args": digest(args),
               "refund_to": dest,
               "dest_source": "tool_result" if hotel else "record"})
    policies = ["refunds-v3"] + (["destination-v1"]
                                 if iso >= FIX_AT else [])
    _tick(clock, 1)
    tw.append({"event": "decision", "run": run, "proposal": pid,
               "bundle": bundle_on(iso), "policies": policies,
               "signed_by": SIGNER, "verdict": "approval"})
    wait = 95 if hotel else rng.randrange(20, 110)
    _tick(clock, wait)
    who = "Teresa Alvarez" if hotel else rng.choice(APPROVERS)
    if hotel:
        tw.append({"event": "approval", "run": run, "proposal": pid,
                   "approver": who, "verdict": "rejected",
                   "why": "card 7731 not on the booking",
                   "wait_s": wait})
        return
    final = dict(args)
    if edit:
        final = dict(args, split=True)
    tw.append({"event": "approval", "run": run, "proposal": pid,
               "approver": who,
               "verdict": "edited" if edit else "approved",
               "args": digest(final), "wait_s": wait})
    _tick(clock, 2)
    tw.append({"event": "execution", "run": run, "proposal": pid,
               "args": digest(final),
               "refund_to": forms if edit else [dest],
               "processor_ref": f"PX-{i + 1:06d}",
               "key": f"{ref}:refund"})
    _tick(clock, 30)
    tw.append({"event": "verified", "run": run, "proposal": pid,
               "ledger": "match", "amount_usd": amount})
    _tick(clock, 1)
    tw.append({"event": "notice", "run": run, "template": "refunded"})


def _tick(clock, seconds: float) -> None:
    clock.t = clock.t + timedelta(seconds=seconds)
