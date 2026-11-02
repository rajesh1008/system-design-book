"""One servicing run, instrumented: the harness loop with a span for
every step, model call, tool call, policy decision and verification.

The loop takes its model, tools, approval desk and verifier as
arguments. Live, they are a scripted planner and the refund world
behind a gateway. In replay (replay.py) they are the recorded answers
read back from the exported trace, so the same loop code runs again
and calls nothing.
"""
from __future__ import annotations

import random
from dataclasses import dataclass, field
from decimal import Decimal

from common import pin
from common.clock import FixedClock
from common.trail import TrailWriter, line_hash
from harness.manifest import load, manifest_hash, resolve, short
from harness.world import Case, World, cases

from . import conventions as c
from .spans import Span, Tracer, digest

AGENT = "servicing"
PROVIDER = "anthropic"
POLICIES = {"refunds-v3": Decimal("1500.00"),
            "refunds-v4-draft": Decimal("500.00")}
EFFECTS = {"refund_ticket", "rebook_ticket", "credit_issue",
           "voucher_issue"}
READS = ("fare_rules_search", "flight_status", "notice_read",
         "offers_search")
TERMINAL = {"customer_notify", "handoff_to_desk"}


def harness(name: str = "servicing-1.0.0") -> dict:
    return resolve(load(name))


def usd(role: str, uncached: int, read: int, out: int) -> Decimal:
    p = pin(role)
    total = (Decimal(str(p.input_usd_per_mtok)) * uncached
             + Decimal(str(p.cache_read_usd_per_mtok)) * read
             + Decimal(str(p.output_usd_per_mtok)) * out)
    return (total / 1_000_000).quantize(Decimal("0.000001"))


def planner_tokens(step: int, cache: bool = True) -> tuple[int, int]:
    """Input tokens of the planner call at `step`, and how many of them
    the prefix cache serves (everything but the newest turn)."""
    tokens_in = 2600 + 700 * step
    cached = 0 if step <= 2 or not cache else 2400 + 700 * (step - 1)
    return tokens_in, min(cached, tokens_in - 200)


# ------------------------------------------------------------- live parts

class Planner:
    """Stands in for the planner model offline: seeded per case, so a
    run is the same every time, and sometimes wrong the way the pilot
    was (an early refund with no permission, a repeated call)."""

    def __init__(self, case: Case, seed: int = 0):
        self.case = case
        self.rng = random.Random(f"plan:{case.cid}:{seed}")
        self.extra = self.rng.choices(
            range(8), weights=(22, 20, 16, 12, 10, 8, 7, 5))[0]
        self.guess = self.rng.random() < 0.04
        self.gives_up = self.rng.random() < 0.02
        self.loops = self.rng.random() < 0.015
        self.last = None

    def tokens_out(self, lo: int = 120, hi: int = 260) -> int:
        return self.rng.randrange(lo, hi)

    def next(self, state: dict) -> dict:
        ref = self.case.booking_ref
        out = self.tokens_out()
        if state["step"] == 1:
            return {"tool": "", "args": {"intent": "refund"},
                    "out_tokens": self.rng.randrange(60, 140)}
        if not state["read"]:
            return dict(tool="booking_read", args={"ref": ref},
                        out_tokens=out)
        if self.gives_up and state["step"] >= 3:
            return dict(tool="handoff_to_desk",
                        args={"why": "model asked"}, out_tokens=out)
        if self.loops and state["step"] >= 3:
            return dict(tool="fare_rules_search",
                        args={"q": "refund rule"}, out_tokens=out)
        if self.extra > 0:
            self.extra -= 1
            pick = self.rng.choice([r for r in READS if r != self.last])
            self.last = pick
            return dict(tool=pick, args={"q": f"{pick}:{self.extra}"},
                        out_tokens=out)
        if self.guess and not state["guessed"]:
            return dict(tool="refund_ticket",
                        args={"ref": ref, "amount": "guess"},
                        out_tokens=out)
        if state["amount"] is None:
            return dict(tool="fare_calc", args={"ref": ref},
                        out_tokens=out)
        if state["amount"] == "0.00":
            return dict(tool="customer_notify",
                        args={"kind": "decline"}, out_tokens=out)
        if state["permit"] is None and not state["denied"]:
            return dict(tool="propose",
                        args={"amount": state["amount"]}, out_tokens=out)
        if state["denied"]:
            return dict(tool="customer_notify",
                        args={"kind": "declined"}, out_tokens=out)
        if not state["refunded"]:
            return dict(tool="refund_ticket",
                        args={"ref": ref, "amount": state["amount"]},
                        out_tokens=out)
        return dict(tool="customer_notify", args={"kind": "refunded"},
                    out_tokens=out)


class Gateway:
    """The tool gateway. Every call through it writes a trail line,
    whether or not anyone made a span for it: the independent record
    the completeness check compares the trace against."""

    def __init__(self, start: str = "2026-06-16T09:00:00-05:00"):
        self.trail = TrailWriter(clock=FixedClock(start, 0.25))

    def call(self, run: str, call_id: str, tool: str, args: dict,
             fn) -> tuple[str, str, str]:
        result = fn()
        verdict = "refused" if result.startswith("refused") else "allowed"
        line = self.trail.append(dict(run=run, call=call_id, tool=tool,
                                      args=digest(args), verdict=verdict))
        return verdict, result, line_hash(line)[:16]


class Tools:
    """The world's tools behind the gateway, for one case."""

    def __init__(self, world: World, case: Case, gateway: Gateway,
                 refuse_reads: float = 0.0, seed: int = 0):
        self.world, self.case, self.gw = world, case, gateway
        self.refuse_reads = refuse_reads
        self.rng = random.Random(f"tools:{case.cid}:{seed}")

    def call(self, call_id: str, tool: str, args: dict,
             permit: str | None = None, key: str = "") -> dict:
        w, case = self.world, self.case
        refused = (tool not in EFFECTS and tool not in TERMINAL
                   and self.rng.random() < self.refuse_reads)

        def fn() -> str:
            if refused:
                return "refused: invalid_arguments"
            if tool == "booking_read":
                return w.booking_read(case)
            if tool == "fare_calc":
                return f"{w.fare_calc(case):.2f}"
            if tool == "refund_ticket":
                amt = case.fare_left if args["amount"] == "guess" \
                    else Decimal(args["amount"])
                return w.refund(case, amt, permit, key)
            if tool == "customer_notify":
                return "sent"
            if tool == "handoff_to_desk":
                return "queued"
            return "ok"

        verdict, result, h = self.gw.call(case.cid, call_id, tool, args,
                                          fn)
        ms = {"refund_ticket": 700, "handoff_to_desk": 90,
              "customer_notify": 150}.get(tool, 120)
        return {"verdict": verdict, "result": result, "trail": h,
                "ms": ms + self.rng.randrange(0, 600 if tool in EFFECTS
                                              else 260)}


class Desk:
    """The refund approver desk: a person, so its answer is recorded."""

    def __init__(self, case: Case):
        self.case = case

    def decide(self, amount: str) -> dict:
        r = random.Random(f"desk:{self.case.cid}")
        return {"approve": self.case.approve,
                "wait_s": r.randrange(20, 110)}


class Verifier:
    """The settlement reconciler: took no part in the run."""

    def __init__(self, world: World, case: Case):
        self.world, self.case = world, case

    def check(self, amount: str) -> dict:
        held = self.world.reconcile(self.case)
        return {"held": f"{held:.2f}", "ok": held == Decimal(amount)}


# ------------------------------------------------------------- the loop

@dataclass
class Result:
    cid: str
    outcome: str = ""
    stop: str = ""
    steps: int = 0
    model_calls: int = 0
    cost: Decimal = Decimal("0")
    trace: list[Span] = field(default_factory=list)
    evidence: dict = field(default_factory=dict)


def run_case(case: Case, h: dict, tracer: Tracer, model, tools, desk,
             verifier, policy: str = "refunds-v3",
             stray: str | None = None, cache: bool = True) -> Result:
    b = h["budgets"]
    cap = Decimal(b["task_usd"])
    stops = {s["id"] for s in h["stops"]}
    res = Result(case.cid)
    st = dict(step=0, read=False, amount=None, permit=None,
              denied=False, refunded=False, guessed=False)
    calls = 0
    last = None

    def tool_span(name: str, args: dict, permit=None, key=""):
        nonlocal calls
        calls += 1
        cid = f"call_{case.cid}_{calls:02d}"
        kind = "effect" if name in EFFECTS else "read"
        if name in TERMINAL:
            kind = "terminal"
        with tracer.span(c.tool_name(name), "INTERNAL", **{
                c.OP: "execute_tool", c.TOOL_NAME: name,
                c.TOOL_CALL: cid, c.TOOL_TYPE: "function",
                c.TOOL_KIND: kind, c.COST: "0.000000"}) as s:
            out = tools.call(cid, name, args, permit, key)
            tracer.advance(out["ms"])
            if s is not None:
                s.attrs[c.VERDICT] = out["verdict"]
                if name in EFFECTS:
                    s.attrs[c.TRAIL] = out["trail"]
                    if permit:
                        s.attrs[c.PERMIT] = permit
                if out["verdict"] == "refused":
                    s.status = "ERROR"
            tracer.record(s, args, out)
        return cid, out

    def chat(role: str, tin: int, tread: int, decision_fn):
        model_id = pin(role).id
        with tracer.span(c.chat_name(model_id), "CLIENT", **{
                c.OP: "chat", c.PROVIDER: PROVIDER,
                c.MODEL: model_id}) as s:
            d = decision_fn()
            tout = d["out_tokens"]
            cost = usd(role, tin - tread, tread, tout)
            tracer.advance(250 + (tin - tread) // 30 + 6 * tout)
            if s is not None:
                s.attrs.update({c.IN_TOKENS: tin, c.OUT_TOKENS: tout,
                                c.CACHE_READ: tread,
                                c.FINISH: ["tool_use"],
                                c.COST: f"{cost:.6f}"})
            tracer.record(s, {"step": st["step"], "role": role}, d)
        res.model_calls += 1
        res.cost += cost
        return d

    def handoff(stop: str):
        tool_span("handoff_to_desk", {"why": stop})
        res.outcome, res.stop = "handed_off", stop

    with tracer.span(c.agent_name(AGENT), "INTERNAL", **{
            c.OP: "invoke_agent", c.PROVIDER: PROVIDER,
            c.AGENT_NAME: AGENT, c.AGENT_VERSION: h["version"],
            c.CONVERSATION: case.cid,
            c.HARNESS_HASH: short(manifest_hash(h))}) as root:
        while not res.outcome:
            if st["step"] >= int(b["steps"]):
                handoff("step_budget")
                break
            tin, tread = planner_tokens(st["step"] + 1, cache)
            if res.cost + usd("mid", tin, 0, 400) > cap:
                handoff("spend_budget")
                break
            st["step"] += 1
            with tracer.span(f"step {st['step']}", **{c.STEP: st["step"]}):
                if st["step"] == 1:
                    chat("small", 900, 0, lambda: model.next(st))
                    continue
                d = chat("mid", tin, tread, lambda: model.next(st))
                tool, args = d["tool"], d["args"]
                this = (tool, digest(args))
                if "no_progress" in stops and this == last:
                    handoff("no_progress")
                    break
                last = this
                if tool == "propose" and case.reason in ("medical",
                                                         "other"):
                    chat("frontier", 5200, 0, lambda: dict(
                        model.next(st), out_tokens=400))
                if tool == "propose":
                    limit = POLICIES[policy]
                    amt = Decimal(args["amount"])
                    ok = (args["amount"] == st["amount"] and amt <= limit)
                    with tracer.span("policy refund", **{
                            c.POLICY: policy,
                            c.AMOUNT: args["amount"]}) as ps:
                        tracer.advance(6)
                        verdict, ans = "refuse", None
                        if ok:
                            ans = desk.decide(args["amount"])
                            verdict = "permit" if ans["approve"] \
                                else "deny"
                        if ps is not None:
                            ps.attrs[c.POLICY_VERDICT] = verdict
                            ps.attrs["lakeshore.decision"] = "refund"
                            if ans:
                                ps.attrs["lakeshore.approval.wait_s"] = \
                                    ans["wait_s"]
                        tracer.record(ps, args, ans)
                    if verdict == "permit":
                        st["permit"] = "PRM-" + digest(
                            [case.cid, args["amount"]])[:8].upper()
                        if ps is not None:
                            ps.attrs[c.PERMIT] = st["permit"]
                    else:
                        st["denied"] = True
                    continue
                key = f"{case.cid}:refund" if st["permit"] else ""
                cid, out = tool_span(tool, args, st["permit"], key)
                r = out["result"]
                if tool == "booking_read" and out["verdict"] == "allowed":
                    st["read"] = True
                elif tool == "fare_calc" and out["verdict"] == "allowed":
                    st["amount"] = r
                elif tool == "refund_ticket":
                    if args["amount"] == "guess":
                        st["guessed"] = True
                    elif r == "ok":
                        st["refunded"] = True
                        with tracer.span("verify refund", **{
                                c.VERIFY_BY: "settlement-reconciler",
                                c.VERIFY_OF: cid}) as vs:
                            tracer.advance(300)
                            v = verifier.check(st["amount"])
                            if vs is not None:
                                vs.attrs[c.VERIFY_RESULT] = \
                                    "match" if v["ok"] else "mismatch"
                            tracer.record(vs, {"of": cid}, v)
                        if not v["ok"]:
                            handoff("verify_failed")
                elif tool == "handoff_to_desk":
                    res.outcome, res.stop = "handed_off", "model_handoff"
                elif tool == "customer_notify":
                    kind = args["kind"]
                    res.outcome = {"refunded": "refunded",
                                   "decline": "declined",
                                   "declined": "declined"}[kind]
                    res.stop = "verified" if kind == "refunded" \
                        else "declined"
        if stray:
            # a fallback path written without the span wrapper: the call
            # goes through the gateway, so the trail has it; the trace
            # does not
            tools.call(f"call_{case.cid}_99", stray, {"kind": "resend"})
        res.steps = st["step"]
        if root is not None:
            root.attrs.update({c.OUTCOME: res.outcome,
                               c.STEPS: res.steps,
                               "lakeshore.stop": res.stop,
                               c.COST: f"{res.cost:.6f}"})
    res.trace, res.evidence = tracer.spans, tracer.evidence
    return res


def live(case: Case, h: dict, world: World, gw: Gateway, start_ms=0,
         skip=(), refuse_reads=0.0, seed=0, stray=None,
         cache=True) -> Result:
    tracer = Tracer(f"{case.cid}:{seed}", start_ms, skip)
    return run_case(case, h, tracer, Planner(case, seed),
                    Tools(world, case, gw, refuse_reads, seed),
                    Desk(case), Verifier(world, case), stray=stray,
                    cache=cache)


@dataclass
class Fleet:
    results: list[Result]
    gateway: Gateway
    world: World


def fleet(n: int = 1000, h: dict | None = None, skip=(),
          refuse_reads=0.0, reconcile_faults=0, seed=0, cache=True,
          stray_every: int = 0) -> Fleet:
    h = h or harness()
    world = World(faults={"reconcile": reconcile_faults})
    gw = Gateway()
    out = [live(cs, h, world, gw, i * 37_000, skip, refuse_reads, seed,
                "customer_notify" if stray_every and i % stray_every == 0
                else None, cache)
           for i, cs in enumerate(cases(n))]
    return Fleet(out, gw, world)
