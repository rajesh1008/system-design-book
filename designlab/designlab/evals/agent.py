"""The agent under test: one refund task, one release, one trial.

A `Release` is whatever the gate is asked to pass: a harness version,
a retrained model, a tool server, a knowledge refresh. Its knobs say
how it behaves differently from the last good release. The run uses
the harness's manifest (hash, context policy, retries) and the
harness's refund world (the ledger and the gateway's refusals), so a
trace carries the same harness version and hash a trail line would.
"""
from __future__ import annotations

import random
from dataclasses import dataclass, field
from decimal import Decimal
from functools import lru_cache

from harness import manifest as M
from harness.loops import SM_ASSESS, SM_INTAKE, Harness, call_cost
from harness.world import ToolTimeout, World

from .golden import GoldenTask

READS = ("booking_read", "fare_calc", "fare_rules_search",
         "flight_status", "notice_read", "doc_intake")


@dataclass(frozen=True)
class Release:
    rid: str
    date: str
    change: str
    kind: str = "model"
    manifest: str = "servicing-1.0.0"
    shape: str = "react"
    fallback_card: bool = False   # server refunds an expired card's
    #                               customer to the card on file
    reason_flip: float = 0.0      # misreads an ambiguous reason
    extra_read: float = 0.025     # an extra rules search
    swap_read: float = 0.012      # reads in another order
    reads_ledger: bool = True     # sees a refund already on the booking
    owner: str = "Daniel Price"


@dataclass
class PayWorld(World):
    """The harness world plus where each refund went."""
    paid_to: dict[str, str] = field(default_factory=dict)


@dataclass
class Trace:
    tid: str
    rid: str
    seed: int
    harness: str
    manifest: str
    calls: list[str] = field(default_factory=list)
    effects: list[tuple[str, ...]] = field(default_factory=list)
    outcome: str = ""
    refused: list[str] = field(default_factory=list)
    reviews: list[str] = field(default_factory=list)
    message: dict = field(default_factory=dict)
    cost: Decimal = Decimal("0")


@lru_cache(maxsize=None)
def harness_for(name: str) -> Harness:
    return Harness(M.resolve(M.load(name)))


def message(t: GoldenTask, tr: Trace, rng: random.Random) -> dict:
    """What the customer is told, as the parts a rubric reads. Most
    messages are complete; some miss the timeline, some are terse,
    a few promise more than policy allows."""
    dest = next((e[2] for e in tr.effects if e[0] == "refund"), None)
    r = rng.random()
    return {"kind": tr.outcome, "amount": t.case.fare_left,
            "card": dest or (t.card if tr.outcome == "already_refunded"
                             else None), "timeline": r >= 0.06,
            "terse": 0.06 <= r < 0.12, "overpromise": 0.12 <= r < 0.14,
            "explains": dest is not None and dest != t.card}


def run(t: GoldenTask, rel: Release, seed: int = 0) -> Trace:
    hz = harness_for(rel.manifest)
    rng = random.Random(f"{t.tid}:{rel.rid}:{seed}")
    w = PayWorld()
    tr = Trace(t.tid, rel.rid, seed, hz.version, hz.hash)
    case = t.case
    sm = rel.shape == "state_machine"
    if t.cls == "already_refunded":
        w.refunds[f"{case.cid}:batch"] = case.fare_left
        w.paid_to[f"{case.cid}:batch"] = t.card
    if t.cls == "tool_timeout":
        w.faults["fare_calc"] = 1
    if t.cls == "two_timeouts":
        w.faults["fare_calc"] = 2

    def call(tool: str) -> None:
        tr.calls.append(tool)
        tr.cost += (SM_INTAKE if sm else call_cost(len(tr.calls)))

    def notify(kind: str) -> None:
        call("customer_notify")
        tr.effects.append(("notice", kind))
        tr.outcome = kind

    def finish() -> Trace:
        tr.message = message(t, tr, rng)
        return tr

    if not sm and rng.random() < rel.swap_read:
        call("fare_rules_search")
    if not hz.ref_visible(case, rng):
        call("customer_notify")          # asks again for the reference
        tr.effects.append(("notice", "ask_ref"))
    call("booking_read")
    if not sm and rng.random() < rel.extra_read:
        call("fare_rules_search")
    if t.cls == "instruction_in_document":
        call("doc_intake")               # a document carries a card
    if t.cls == "already_refunded" and rel.reads_ledger:
        notify("already_refunded")
        return finish()
    eligible = case.eligible
    if t.cls == "ambiguous_reason" and rng.random() < rel.reason_flip:
        eligible = False                 # read as changed plans
    if sm:
        tr.cost += SM_ASSESS
    call("fare_calc")
    try:
        amount = hz.with_retries(w.fare_calc, case)
    except ToolTimeout:
        tr.outcome = "handed_off"
        return finish()
    if amount == 0 or not eligible:
        notify("declined")
        return finish()
    call("propose")
    if t.cls == "instruction_in_document":
        tr.reviews.append("tier 3 reviewer rejected: card not on file")
        tr.outcome = "handed_off"        # the proposal reached a queue
        return finish()
    if not case.approve:
        notify("not_approved")
        return finish()
    permit, key = f"P-{case.cid}", f"{case.cid}:refund"
    dest = t.card
    if rel.fallback_card and t.expired and t.card_on_file:
        dest = t.card_on_file
    call("refund_ticket")
    r = w.refund(case, amount, permit, key)
    if r == "ok":
        w.paid_to[key] = dest
        tr.effects.append(("refund", f"{amount:.2f}", dest))
    else:
        tr.refused.append(r)
    if w.reconcile(case) > 0:
        notify("refunded")
    else:
        tr.outcome = "handed_off"
    return finish()
