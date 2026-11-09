"""The rebooking saga, ordered by reversibility (Chapter 7).

A rebooking touches four systems that cannot share a transaction. Each
step is its own keyed effect with its own compensation. The order puts
the cheapest undo first and the step that cannot be undone (giving up
the old seat) as late as possible, so a failure before it leaves the
traveler exactly where they started.

    SAFE    hold new seat, charge fare difference, issue new ticket,
            cancel old segment (the pivot), notify
    PILOT   cancel old segment, charge, issue new ticket, notify

The pilot's order is the one that stranded a traveler: the old flight
was canceled first and the new ticket then failed.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from chain.record import Permission
from common.rand import DEFAULT_SEED, seeded
from corpus.tools import LOOKUP, NATIVE, NONE, SupplierSim, ToolSpec, spec
from .execute import Executor
from .keys import KeyIssuer
from .ledger import Ledger

RELEASE = ToolSpec("airline-release-hold", "airline", "release a hold",
                   NATIVE, "", 0)

# step name -> (tool, compensation tool or None)
STEPS = {
    "hold": ("airline-seat-hold", "airline-release-hold"),
    "charge": ("fare-charge", "processor-refund"),
    "issue": ("airline-rebook-b", "airline-void-ticket"),
    "cancel-old": ("airline-cancel-segment", None),
    "notify": ("customer-email", None),
}
SAFE = ("hold", "charge", "issue", "cancel-old", "notify")
PILOT = ("cancel-old", "charge", "issue", "notify")


@dataclass
class SagaRun:
    order: tuple[str, ...]
    done: list[str] = field(default_factory=list)
    failed_at: str = ""
    why: str = ""
    compensated: list[str] = field(default_factory=list)
    for_people: list[str] = field(default_factory=list)
    old_seat: bool = True
    new_ticket: bool = False

    @property
    def stranded(self) -> bool:
        return not self.old_seat and not self.new_ticket


def _sims(override: dict[str, str] | None) -> dict[str, SupplierSim]:
    sims = {}
    for step, (tool, comp) in STEPS.items():
        for name in filter(None, (tool, comp)):
            t = RELEASE if name == RELEASE.name else spec(name)
            sim = SupplierSim(t)
            if override and name in override:
                sim.honor_keys = {NATIVE: True, NONE: False}[override[name]]
            sims[name] = sim
    return sims


def run_saga(order=SAFE, fail_step: str = "", fail_kind: str = "refused",
             override: dict[str, str] | None = None, run: int = 0,
             ledger: Ledger | None = None) -> SagaRun:
    """`fail_kind` is "refused" (the supplier says no) or "timeout"
    (every call to that step times out with the effect not applied)."""
    ledger = ledger or Ledger()
    sims = _sims(override)
    issuer = KeyIssuer()
    perm = Permission(f"PRM-{70000 + run}", "policy-engine", "lab", 800.0)
    state = SagaRun(tuple(order))

    def faults(name: str) -> str:
        tool = STEPS.get(fail_step, ("", ""))[0]
        return "lost" if fail_kind == "timeout" and name == tool else ""

    ex = Executor(ledger, sims, faults=faults)
    for step in order:
        tool, _ = STEPS[step]
        req = {"intent": f"RB-{run:05d}-{step}", "target": f"LTG-R{run}",
               "step": step}
        ek = issuer.mint(perm, tool, req, at=ex.now)
        if step == fail_step and fail_kind == "refused":
            ledger.reserve(ek, ex.now)
            tok = ledger.acquire(ek.key, "action-executor", ex.now)
            ledger.move(ek.key, "attempting", ex.now, "attempt 1", tok)
            ledger.move(ek.key, "failed", ex.now, "supplier refused", tok)
            state.failed_at, state.why = step, "refused"
            break
        e = ex.run(ek, req)
        if e.state != "committed":
            state.failed_at, state.why = step, e.state
            if e.state == "escalated":
                state.for_people.append(step)
            break
        state.done.append(step)
        if step == "cancel-old":
            state.old_seat = False
        if step == "issue":
            state.new_ticket = True
    if state.failed_at and state.failed_at != "notify":
        for step in reversed(state.done):
            _, comp = STEPS[step]
            if comp is None:
                continue   # past the pivot: nothing to undo
            req = {"intent": f"RB-{run:05d}-undo-{step}",
                   "target": f"LTG-R{run}", "step": f"undo-{step}"}
            ek = issuer.mint(perm, comp, req, at=ex.now)
            if ex.run(ek, req).state == "committed":
                state.compensated.append(comp)
                if step == "issue":
                    state.new_ticket = False
            else:
                state.for_people.append(f"undo-{step}")
    return state


def inject(n: int = 1_000, order=SAFE, seed: int = DEFAULT_SEED
           ) -> dict[str, int]:
    """Fail one step per run, chosen at random, and count the outcomes."""
    rng = seeded(seed, "effects", "saga", "-".join(order))
    out = {"runs": n, "stranded": 0, "restored": 0, "rebooked": 0,
           "to a person": 0}
    for i in range(n):
        step = rng.choice(order)
        kind = rng.choice(("refused", "timeout"))
        s = run_saga(order, step, kind, run=i)
        if s.stranded:
            out["stranded"] += 1
        elif s.new_ticket:
            out["rebooked"] += 1
        else:
            out["restored"] += 1
        if s.for_people:
            out["to a person"] += 1
    return out
