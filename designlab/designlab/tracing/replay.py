"""Replay from the trace.

Strict replay: read the exported trace, hand the harness loop the
recorded answers in place of the model, the tools, the desk and the
verifier, run the same loop code, and diff the new span sequence
against production. Nothing live is called: an answer the trace does
not hold falls through to `NoCalls`, which raises.

What-if replay: the same, under a changed harness or policy. The first
place the new run asks for something production never asked for is
the divergence, and the diff names it.
"""
from __future__ import annotations

import time
from dataclasses import dataclass

from durable.bench import pct
from durable.replay import NoCalls
from harness.world import Case

from . import conventions as c
from .run import EFFECTS, run_case
from .spans import Span, Tracer, digest, export, load


class Diverged(Exception):
    pass


class _Tape:
    def __init__(self, spans: list[Span], evidence: dict, prefix: str):
        self.items = [(s, evidence[s.span_id]) for s in spans
                      if s.name.startswith(prefix)
                      and s.span_id in evidence]
        self.i = 0

    def next(self, what: str):
        if self.i >= len(self.items):
            NoCalls().call()                 # raises: called out
        s, ev = self.items[self.i]
        self.i += 1
        return s, ev


class RecordedModel:
    def __init__(self, tape: _Tape):
        self.tape = tape

    def next(self, state: dict) -> dict:
        s, ev = self.tape.next("model")
        return dict(ev["out"])


class RecordedTools:
    def __init__(self, tape: _Tape):
        self.tape = tape

    def call(self, call_id, tool, args, permit=None, key="") -> dict:
        s, ev = self.tape.next("tool")
        if s.attrs[c.TOOL_NAME] != tool or ev["in"] != args:
            raise Diverged(f"asked {tool}, trace has "
                           f"{s.attrs[c.TOOL_NAME]}")
        if c.TRAIL in s.attrs and s.attrs.get(c.PERMIT) != permit:
            raise Diverged(f"{tool} with permit {permit}, trace has "
                           f"{s.attrs.get(c.PERMIT)}")
        return dict(ev["out"])


class RecordedDesk:
    def __init__(self, tape: _Tape):
        self.tape = tape

    def decide(self, amount: str) -> dict:
        s, ev = self.tape.next("desk")
        if ev["out"] is None:
            raise Diverged("desk asked; production never asked it")
        return dict(ev["out"])


class RecordedVerifier:
    def __init__(self, tape: _Tape):
        self.tape = tape

    def check(self, amount: str) -> dict:
        s, ev = self.tape.next("verify")
        return dict(ev["out"])


SIG = (c.TOOL_NAME, c.ARGS_DIGEST, c.VERDICT, c.POLICY_VERDICT,
       c.AMOUNT, c.PERMIT, c.VERIFY_RESULT, c.OUTCOME, c.STEPS,
       "lakeshore.stop", c.COST, c.IN_TOKENS, c.OUT_TOKENS)


def signature(s: Span) -> tuple:
    return (s.name,) + tuple(s.attrs.get(k) for k in SIG)


@dataclass
class Diff:
    same: bool
    index: int = -1
    production: str = ""
    replay: str = ""
    note: str = ""


def diff(prod: list[Span], new: list[Span]) -> Diff:
    # the root's summary (outcome, steps, cost) is written last, so it
    # is compared last: the first difference is where the run turned
    a = [signature(s) for s in prod[1:] + prod[:1]]
    b = [signature(s) for s in new[1:] + new[:1]]
    for i, (x, y) in enumerate(zip(a, b)):
        if x != y:
            fields = [SIG[j].split(".", 1)[1] for j in range(len(SIG))
                      if x[j + 1] != y[j + 1]]
            what = "name" if x[0] != y[0] else ", ".join(fields)
            return Diff(False, (i + 1) % len(a), x[0], y[0], what)
    if len(a) != len(b):
        i = min(len(a), len(b))
        return Diff(False, i + 1, a[i][0] if i < len(a) else "(end)",
                    b[i][0] if i < len(b) else "(end)", "length")
    return Diff(True)


@dataclass
class Replayed:
    diff: Diff
    spans: list[Span]
    outcome: str
    stop: str
    error: str = ""
    seconds: float = 0.0


def replay(case: Case, text: str, h: dict, policy: str = "refunds-v3",
           start_ms: int = 0) -> Replayed:
    """Replay one run from its exported trace text."""
    t0 = time.perf_counter()
    spans, evidence = load(text)
    root = spans[0]
    tracer = Tracer(f"replay:{root.trace_id}", start_ms)
    err = ""
    try:
        r = run_case(case, h, tracer,
                     RecordedModel(_Tape(spans, evidence, "chat ")),
                     RecordedTools(_Tape(spans, evidence, "execute_tool ")),
                     RecordedDesk(_Tape(spans, evidence, "policy ")),
                     RecordedVerifier(_Tape(spans, evidence, "verify ")),
                     policy=policy)
        out, stop = r.outcome, r.stop
    except (Diverged, AssertionError) as e:
        err, out, stop = str(e), "", ""
    new = tracer.spans
    d = diff(spans, new)
    if err and d.same:
        d = Diff(False, len(new), "", "", err)
    return Replayed(d, new, out, stop, err, time.perf_counter() - t0)


def bench(fl, h: dict) -> dict:
    """Strict-replay every run in a fleet from its exported trace."""
    times, diverged = [], 0
    by_cid = {}
    from harness.world import cases
    for cs in cases(len(fl.results)):
        by_cid[cs.cid] = cs
    for r in fl.results:
        text = export(r.trace, r.evidence)
        rp = replay(by_cid[r.cid], text, h)
        times.append(rp.seconds * 1000)
        diverged += not rp.diff.same
    return {"runs": len(times), "diverged": diverged,
            "p50_ms": pct(times, 50), "p95_ms": pct(times, 95),
            "max_ms": max(times)}


def trace_digest(spans: list[Span]) -> str:
    return digest([signature(s) for s in spans])


def production_times(n: int = 2000, seed: int = 35) -> list[float]:
    """Seconds to replay one run in Lakeshore's benchmark: fetching the
    trace and its evidence from the trace store, then the compute this
    module measures. Illustrative: a seeded model of the shape Ben
    Carter's benchmark reports (median about 1.7 s), not a measurement
    taken here. The lab measures only the compute part."""
    import math
    import random
    rng = random.Random(seed)
    out = []
    for _ in range(n):
        fetch = 1.63 * math.exp(rng.gauss(0, 0.075))
        compute = 0.04 + rng.random() * 0.06
        out.append(round(fetch + compute, 3))
    return out
