"""The harness test suite: what the harness does, with the model held
still or replaced by a script that misbehaves on purpose.

Four groups, as in Section 6: Stop Conditions, Budgets, tool errors and
the context policy, plus transitions when the manifest declares a state
machine. A check takes the resolved manifest and returns a reason when
it fails. None of these checks asks whether the model is good.
"""
from __future__ import annotations

import random
from dataclasses import replace
from decimal import Decimal

from cost.budget import Limits

from . import loops
from .world import Case, World, cases

CASE = cases(1)[0]
LONG = replace(CASE, turns=12, eligible=True, approve=True)


class Wander:
    """Never repeats itself and never finishes."""

    def __init__(self):
        self.n = 0

    def next(self, s):
        self.n += 1
        return "fare_rules_search", {"q": f"rule {self.n}"}


class Repeat:
    def next(self, s):
        return "flight_status", {"id": "FLT-100200"}


class Claims:
    """Says it is done without doing anything."""

    def next(self, s):
        return "finish", {"summary": "refund complete"}


class Unknown:
    def __init__(self):
        self.sent = False

    def next(self, s):
        if not self.sent:
            self.sent = True
            return "refund_everything", {}
        return "handoff_to_desk", {}


def _hz(h):
    return loops.Harness(h, trail=loops.new_trail())


def _happy(case=LONG, seed=1):
    """A ScriptedModel run with no wandering, so faults decide it."""
    def make(c):
        m = loops.ScriptedModel(c, random.Random(seed))
        m.opt = m.early_refund = m.early_notify = m.dup = 0
        return m
    return make(case)


# -- Stop Conditions --------------------------------------------------

def stop_step_budget(h):
    r = loops.react(CASE, _hz(h), model=Wander())
    if (r.stop, r.steps) != ("step_budget", int(h["budgets"]["steps"])):
        return f"wandering model ended {r.stop} at step {r.steps}"


def stop_no_progress(h):
    r = loops.react(CASE, _hz(h), model=Repeat())
    if (r.stop, r.steps) != ("no_progress", 2):
        return f"repeated call ended {r.stop} at step {r.steps}"


def stop_claim_is_not_done(h):
    r = loops.react(LONG, _hz(h), model=Claims())
    if r.outcome == "done":
        return "the model's own claim ended the run as done"


def stop_verified_needs_effect(h):
    w = World()
    r = loops.react(LONG, _hz(h), model=_happy(), world=w)
    if r.outcome == "done" and w.reconcile(LONG) != LONG.fare_left:
        return "done without the processor holding the refund"
    if r.outcome != "done":
        return f"clean run ended {r.outcome} ({r.stop})"


class GivesUp:
    def next(self, s):
        return "handoff_to_desk", {"why": "customer asked for a person"}


def stop_model_may_hand_off(h):
    r = loops.react(CASE, _hz(h), model=GivesUp())
    if (r.outcome, r.steps) != ("handed_off", 1):
        return f"a hand-off at step 1 ended {r.outcome}"


# -- Budgets ------------------------------------------------------------

def budget_spend(h):
    hz = _hz(h)
    hz.cap = Decimal("0.10")          # a small cap, so the test is quick
    r = loops.react(CASE, hz, model=Wander())
    if r.stop != "spend_budget" or r.cost > hz.cap:
        return f"ended {r.stop} having spent ${r.cost:.4f}"


def budget_matches_enforcer(h):
    lim, b = Limits(), h["budgets"]
    bad = []
    if Decimal(b["task_usd"]) != Decimal(str(lim.task_usd)).quantize(
            Decimal("0.01")):
        bad.append(f"task_usd {b['task_usd']} vs enforcer "
                   f"{lim.task_usd:.2f}")
    if int(b["model_calls"]) != lim.task_steps:
        bad.append(f"model_calls {b['model_calls']} vs "
                   f"{lim.task_steps}")
    return "; ".join(bad) or None


def budget_calls_counted(h):
    r = loops.react(CASE, _hz(h), model=Wander())
    if r.model_calls > int(h["budgets"]["model_calls"]):
        return f"{r.model_calls} model calls"


def budget_stop_leaves_trail(h):
    hz = _hz(h)
    loops.react(CASE, hz, model=Wander())
    last = hz.trail.lines[-1]
    if '"stop": "step_budget"' not in last or hz.hash not in last:
        return "the budget stop is not in the trail with the hash"


# -- Tool errors --------------------------------------------------------

def tool_timeout_retried(h):
    w = World(faults={"fare_calc": 1})
    r = loops.react(LONG, _hz(h), model=_happy(), world=w)
    if r.outcome != "done":
        return f"one fare_calc timeout ended the case {r.stop}"


def tool_timeout_hands_off(h):
    w = World(faults={"fare_calc": 5})
    r = loops.react(LONG, _hz(h), model=_happy(), world=w)
    if r.stop != "tool_error" or w.refunds:
        return f"repeated timeouts ended {r.stop}, refunds {w.refunds}"


def tool_refusal_not_effect(h):
    w = World()
    m = _happy()
    m.early_refund = True
    r = loops.react(LONG, _hz(h), model=m, world=w)
    if "refused: no permission" not in r.refused or \
            w.reconcile(LONG) != LONG.fare_left:
        return "a refusal was not refused, or the case did not finish"


def tool_unknown_refused(h):
    r = loops.react(CASE, _hz(h), model=Unknown())
    if "unknown tool refund_everything" not in r.refused:
        return "an unknown tool name ran"


# -- Context policy -----------------------------------------------------

def context_ref_survives(h):
    asks = sum(loops.react(LONG, _hz(h), model=_happy(seed=i),
                           seed=i).reasks for i in range(20))
    if asks:
        return f"booking reference re-asked in {asks} of 20 long runs"


def context_pins_effects(h):
    need = {"permission_ids", "idempotency_keys", "amounts"}
    miss = need - set(h["context"]["pin"])
    return f"not pinned: {sorted(miss)}" if miss else None


def context_within_budget(h):
    c = h["context"]
    worst = 2600 + 700 * int(h["budgets"]["steps"])
    if worst > c["budget_tokens"] * c["compact_at"]:
        return f"step-24 context {worst} tokens passes the threshold"


# -- Transitions (state machine only) ------------------------------------

def transitions_allowed(h):
    allowed, _ = loops.transitions(h)
    seen = set()
    runs = [dict(), dict(intake=lambda c: "unclear"),
            dict(assess=lambda c: None)]
    runs += [dict(world=World(faults={f: 5})) for f in
             ("booking_read", "fare_calc", "refund_ticket", "reconcile")]
    for c in cases(50):
        for kw in runs:
            if "world" in kw:
                kw = dict(kw, world=World(faults=dict(kw["world"].faults)))
            r = loops.state_machine(c, _hz(h), **kw)
            seen |= set(zip(r.path, r.path[1:] + [r.outcome]))
    unc = sorted(set(allowed) - seen)
    return f"never reached: {unc}" if unc else None


def transitions_forbidden(h):
    _, forbidden = loops.transitions(h)
    c = replace(CASE, eligible=True, approve=True)
    leaks = [f"{a}->{b}" for a, b in forbidden
             if loops.state_machine(c, _hz(h), force=(a, b)).stop
             != "illegal_transition"]
    return f"not refused: {leaks}" if leaks else None


GROUPS = {
    "stops": [stop_step_budget, stop_no_progress, stop_claim_is_not_done,
              stop_verified_needs_effect, stop_model_may_hand_off],
    "budgets": [budget_spend, budget_matches_enforcer,
                budget_calls_counted, budget_stop_leaves_trail],
    "tool errors": [tool_timeout_retried, tool_timeout_hands_off,
                    tool_refusal_not_effect, tool_unknown_refused],
    "context": [context_ref_survives, context_pins_effects,
                context_within_budget],
    "transitions": [transitions_allowed, transitions_forbidden],
}


def run(h: dict) -> list[tuple[str, str, str | None]]:
    """(group, check, failure or None) for every check that applies."""
    sm = "tasks" in h["loop"]
    out = []
    for g, checks in GROUPS.items():
        if g == "transitions" and not sm:
            continue
        for fn in checks:
            out.append((g, fn.__name__, fn(h)))
    return out
