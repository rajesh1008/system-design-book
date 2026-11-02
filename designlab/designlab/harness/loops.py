"""Two loop shapes for one refund case, both run by the harness.

`react` lets the model choose every next step; the harness holds the
Stop Conditions, the Budgets and the context policy around it. `state_
machine` runs the states and transitions the manifest declares; the
model fills two of them (intake and assess) and never picks the next
state. Both write the harness version and manifest hash into every
trail line, and both count illegal transitions: steps the gateway or
the transition table refused.
"""
from __future__ import annotations

import json
import random
from dataclasses import dataclass, field
from decimal import Decimal

from common.clock import FixedClock
from common.trail import TrailWriter

from .manifest import manifest_hash, short
from .world import Case, ToolTimeout, World

# Prices per million tokens for the roles the loop uses (models.toml).
MID_IN, MID_OUT = Decimal("2.00"), Decimal("10.00")
SMALL_IN, SMALL_OUT = Decimal("0.10"), Decimal("0.50")
SUMMARY_KEEPS = 0.85      # a fact left to the summary survives this often
GIVES_UP = 0.30           # a customer asked twice who asks for a person


def call_cost(step: int) -> Decimal:
    """One ReAct planner call on mid: the context grows every step."""
    tokens_in = 2600 + 700 * step
    return (tokens_in * MID_IN + 180 * MID_OUT) / 1_000_000


SM_INTAKE = (900 * SMALL_IN + 120 * SMALL_OUT) / 1_000_000
SM_ASSESS = (3400 * MID_IN + 250 * MID_OUT) / 1_000_000


@dataclass
class Run:
    cid: str
    shape: str
    outcome: str = ""         # done, declined, handed_off
    stop: str = ""            # which Stop Condition ended it
    steps: int = 0
    illegal: int = 0
    reasks: int = 0
    model_calls: int = 0
    cost: Decimal = Decimal("0")
    path: list[str] = field(default_factory=list)
    refused: list[str] = field(default_factory=list)


class Harness:
    """What both shapes share: the resolved manifest, the trail and the
    context policy."""

    def __init__(self, h: dict, trail: TrailWriter | None = None,
                 echo: str = "claude-sonnet-5-5"):
        self.h = h
        self.version = h["version"]
        self.hash = short(manifest_hash(h))
        self.stops = {s["id"] for s in h["stops"]}
        self.b = h["budgets"]
        self.cap = Decimal(self.b["task_usd"])
        self.tools = {t["name"]: t for t in h["tools"]}
        self.trail = trail
        self.echo = echo

    def log(self, run: Run, what: str, **kw) -> None:
        if self.trail is not None:
            self.trail.append(dict(run=run.cid, step=run.steps, what=what,
                                   harness=self.version,
                                   manifest=self.hash, **kw))

    def ref_visible(self, case: Case, rng: random.Random) -> bool:
        """Is the booking reference in what the model sees? It is when
        pinned, when its turn is still verbatim, or when the summary of
        older turns happened to keep it."""
        c = self.h["context"]
        if "booking_ref" in c["pin"] or case.turns <= c["keep_turns"]:
            return True
        return rng.random() < SUMMARY_KEEPS

    def with_retries(self, fn, *args):
        tries = 1 + int(self.b["tool_retries"])
        for _ in range(tries):
            try:
                return fn(*args)
            except ToolTimeout:
                continue
        raise ToolTimeout("retries spent")


# ---------------------------------------------------------------- ReAct

OPTIONAL = [("fare_rules_search", {"q": "refund rule"}),
            ("fare_rules_search", {"q": "schedule change waiver"}),
            ("fare_rules_search", {"q": "refundable fare product"}),
            ("flight_status", {}), ("notice_read", {"id": "N-1"}),
            ("notice_read", {"id": "N-2"}), ("offers_search", {}),
            ("code_run", {"expr": "fare minus fee"}),
            ("booking_read", {"why": "segments"})]
OPT_WEIGHTS = (20, 17, 14, 11, 9, 7, 6, 5, 4, 3, 2, 2)


class ScriptedModel:
    """Stands in for the planner model offline: plausible, variable and
    sometimes wrong in the ways the pilot was (Section 2)."""

    def __init__(self, case: Case, rng: random.Random):
        self.case, self.rng = case, rng
        self.opt = rng.choices(range(12), weights=OPT_WEIGHTS)[0]
        self.early_refund = rng.random() < 0.05
        self.early_notify = rng.random() < 0.04
        self.dup = rng.random() < 0.03
        self.check = rng.random() < 0.25
        self.did: set[str] = set()
        self.last = None

    def _once(self, flag: str) -> bool:
        if flag in self.did:
            return False
        self.did.add(flag)
        return True

    def next(self, s: dict) -> tuple[str, dict]:
        ref = {"ref": self.case.booking_ref}
        if not s["ref_visible"]:
            return "customer_notify", {"kind": "ask_ref"}
        if not s["read"]:
            return "booking_read", ref
        if self.opt > 0:
            self.opt -= 1
            if self.last and self.rng.random() < 0.03:
                return self.last          # the same call again
            self.last = self.rng.choice([o for o in OPTIONAL
                                         if o != self.last])
            return self.last
        if self.early_refund and s["permit"] is None \
                and self._once("early_refund"):
            return "refund_ticket", dict(ref, amount="guess")
        if s["amount"] is None:
            return "fare_calc", ref
        if s["amount"] == 0:
            return "customer_notify", {"kind": "decline"}
        if self.early_notify and not s["refunded"] \
                and self._once("early_notify"):
            return "customer_notify", {"kind": "refunded"}
        if s["permit"] is None:
            return "propose", {"amount": str(s["amount"])}
        if not s["refunded"]:
            return "refund_ticket", dict(ref, amount=str(s["amount"]))
        if self.dup and self._once("dup"):
            return "refund_ticket", dict(ref, amount=str(s["amount"]),
                                         again=True)
        if self.check and self._once("check"):
            return "booking_read", dict(ref, why="confirm")
        return "customer_notify", {"kind": "refunded"}


def react(case: Case, hz: Harness, seed: int = 0,
          world: World | None = None, model=None) -> Run:
    rng = random.Random(f"{case.cid}:{seed}")
    world = world or World()
    model = model or ScriptedModel(case, rng)
    run = Run(case.cid, "react")
    s = {"ref_visible": hz.ref_visible(case, rng), "read": False,
         "amount": None, "permit": None, "refunded": False}
    last = None
    key = f"{case.cid}:refund"

    def end(outcome: str, stop: str) -> Run:
        run.outcome, run.stop = outcome, stop
        hz.log(run, "stop", outcome=outcome, stop=stop)
        return run

    while True:
        if run.steps >= int(hz.b["steps"]):
            return end("handed_off", "step_budget")
        price = call_cost(run.steps + 1)
        if run.cost + price > hz.cap:
            return end("handed_off", "spend_budget")
        tool, args = model.next(s)
        run.steps += 1
        run.model_calls += 1
        run.cost += price
        run.path.append(tool)
        hz.log(run, "call", tool=tool, model=hz.echo)
        this = (tool, json.dumps(args, sort_keys=True))
        if "no_progress" in hz.stops and this == last:
            return end("handed_off", "no_progress")
        last = this
        if tool not in hz.tools and tool != "propose":
            run.refused.append(f"unknown tool {tool}")
            continue
        if tool == "handoff_to_desk":
            return end("handed_off", "model_handoff")
        if tool == "booking_read":
            s["read"] = True
        elif tool == "fare_calc":
            try:
                s["amount"] = hz.with_retries(world.fare_calc, case)
            except ToolTimeout:
                return end("handed_off", "tool_error")
        elif tool == "propose":
            if s["amount"] is None:
                run.refused.append("propose without an amount")
                continue
            if not case.approve:
                return end("declined", "verified")
            s["permit"] = f"P-{case.cid}"
        elif tool == "refund_ticket":
            amount = (Decimal(args["amount"]) if args["amount"] != "guess"
                      else case.fare_left)
            try:
                r = hz.with_retries(world.refund, case, amount,
                                    s["permit"], key)
            except ToolTimeout:
                return end("handed_off", "tool_error")
            if r == "ok":
                s["refunded"] = True
            else:
                run.illegal += 1
                run.refused.append(r)
        elif tool == "customer_notify":
            kind = args.get("kind")
            if kind == "ask_ref":
                run.reasks += 1
                s["ref_visible"] = True
                if rng.random() < GIVES_UP:
                    return end("handed_off", "customer_asked")
                continue
            held = world.reconcile(case)
            if kind == "decline" and held == 0 and not case.eligible:
                return end("declined", "verified")
            if kind == "refunded" and held > 0:
                world.notices.append((case.cid, kind))
                return end("done", "verified")
            run.illegal += 1          # told the customer before the fact
            run.refused.append("outcome not verified")
        elif tool == "finish":
            if world.reconcile(case) > 0:
                return end("done", "verified")
            return end("handed_off", "unverified")


# -------------------------------------------------------- state machine

class IllegalTransition(RuntimeError):
    pass


def table(h: dict, task: str = "refund") -> tuple[dict, list[str], str]:
    spec = h["loop"]["tasks"][task]
    return ({s: list(v[1:]) for s, v in spec["states"].items()},
            list(spec["terminals"]), spec["start"])


def transitions(h: dict, task: str = "refund"):
    """(allowed, forbidden) pairs, terminals included as targets."""
    t, terminals, _ = table(h, task)
    every = list(t) + terminals
    allowed = [(a, b) for a in t for b in t[a]]
    forbidden = [(a, b) for a in t for b in every
                 if b not in t[a] and b != a]
    return allowed, forbidden


def default_intake(case: Case) -> str:
    return case.reason


def default_assess(case: Case) -> bool:
    return case.eligible


def state_machine(case: Case, hz: Harness, world: World | None = None,
                  intake=default_intake, assess=default_assess,
                  force: tuple[str, str] | None = None) -> Run:
    """`force` makes one state return a target of the test's choosing,
    so a test can try every forbidden transition."""
    world = world or World()
    t, terminals, state = table(hz.h)
    run = Run(case.cid, "state_machine")
    v: dict = {"key": f"{case.cid}:refund"}

    def step(state: str) -> str:
        if state == "intake":
            run.model_calls += 1
            run.cost += SM_INTAKE
            v["reason"] = intake(case)
            return "handed_off" if v["reason"] == "unclear" else "gather"
        if state == "gather":
            try:                                # held in state, not text
                v["booking"] = hz.with_retries(world.booking_read, case)
            except ToolTimeout:
                return "handed_off"
            return "assess"
        if state == "assess":
            run.model_calls += 1
            run.cost += SM_ASSESS
            v["eligible"] = assess(case)
            return "handed_off" if v["eligible"] is None else "propose"
        if state == "propose":
            if not v["eligible"]:
                v["amount"] = Decimal("0.00")
                return "permit"
            try:
                v["amount"] = hz.with_retries(world.fare_calc, case)
            except ToolTimeout:
                return "handed_off"
            return "permit"
        if state == "permit":
            if v["amount"] == 0 or not case.approve:
                return "declined"
            v["permit"] = f"P-{case.cid}"
            return "execute"
        if state == "execute":
            try:
                r = hz.with_retries(world.refund, case, v["amount"],
                                    v["permit"], v["key"])
            except ToolTimeout:
                return "handed_off"
            return "verify" if r in ("ok", "duplicate: no new effect") \
                else "handed_off"
        if state == "verify":
            return ("done" if world.reconcile(case) == v["amount"]
                    else "handed_off")
        raise IllegalTransition(f"no handler for {state}")

    while state not in terminals:
        if run.steps >= int(hz.b["steps"]):
            run.outcome, run.stop = "handed_off", "step_budget"
            break
        run.steps += 1
        run.path.append(state)
        nxt = step(state)
        if force and state == force[0]:
            nxt = force[1]
        hz.log(run, "state", state=state, next=nxt)
        if nxt not in t[state]:
            run.illegal += 1
            run.refused.append(f"{state} -> {nxt}")
            run.outcome, run.stop = "handed_off", "illegal_transition"
            hz.log(run, "stop", outcome=run.outcome, stop=run.stop)
            return run
        state = nxt
    if not run.outcome:
        run.outcome = state
        run.stop = "verified" if state in ("done", "declined") else "handoff"
    hz.log(run, "stop", outcome=run.outcome, stop=run.stop)
    return run


def new_trail(start: str = "2026-06-08T09:00:00-05:00") -> TrailWriter:
    return TrailWriter(clock=FixedClock(start, step_seconds=2.0))
