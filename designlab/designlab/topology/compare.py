"""Single agent against orchestrator-worker on the golden set (Chapter 27).

A seeded, mechanistic simulation, not a model run. Each case is run
three times by each topology, paired by case and repeat. What drives
the result is written down as parameters, so a reader can change one
and see which wins move:

single agent   one loop and one context. Calls grow with legs, and
               faster than linearly past two legs, because the loop
               re-reads and reconciles earlier legs. Chapter 18's task
               budget (24 model calls) stops the run, and a stopped
               run goes to a person. Each extra leg in one context
               costs a little accuracy.
orchestrator-  a lead plans, briefs one worker per leg and one per
worker         specialist, merges their summaries, and checks before
               the effect. Workers run in parallel with small
               contexts. Every brief can drop a fact the worker
               needed, and the merge can get a summary wrong. The
               briefs, worker prompts, summaries, and merge are the
               coordination tokens.

A type is won when the paired difference in verified success is more
than two standard errors; otherwise it is a tie, and a tie goes to the
design with fewer tokens per verified outcome.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field

from common.rand import seeded
from harness.manifest import load as load_manifest

from .tasks import TYPES, Case, golden_set

# Chapter 18's per-task call budget, as Chapter 25's harness declares it
# (servicing-1.0.0, [budgets] model_calls). Every agent in a task is
# charged to this one counter.
CALL_CAP = int(load_manifest("servicing-1.0.0")["budgets"]["model_calls"])
REPEATS = 3
SECONDS_PER_CALL = 2.2
OUT_PER_CALL = 250     # output tokens per call

# Single agent: base calls, quality, context growth per call.
BASE_CALLS = {"voluntary-rebook": 10, "involuntary-rebook": 10,
              "schedule-change-accept": 10, "cancel-for-credit": 7,
              "cancel-with-refund": 8, "involuntary-refund": 8,
              "hotel-cancel": 6, "hotel-date-change": 7, "upgrade": 7,
              "ancillary-refund": 6, "car-rental-change": 7,
              "name-correction": 6}
QUALITY = {"voluntary-rebook": 0.965, "involuntary-rebook": 0.96,
           "schedule-change-accept": 0.965, "cancel-for-credit": 0.975,
           "cancel-with-refund": 0.97, "involuntary-refund": 0.965,
           "hotel-cancel": 0.975, "hotel-date-change": 0.97,
           "upgrade": 0.97, "ancillary-refund": 0.975,
           "car-rental-change": 0.97, "name-correction": 0.975}
SYSTEM_TOKENS = 3_000
CONTEXT_GROWTH = 500    # tokens added to the context by each call
LEG_CALLS = 5            # extra calls per extra leg, searching types
LEG_PENALTY = 0.02       # accuracy lost per extra leg in one context

# Orchestrator-worker.
LEAD_CALLS = 4           # plan, merge, check, effect
LEAD_EXTRA = 3_000       # the lead's own orchestration instructions
WORKER_SYSTEM = 5_400
BRIEF_TOKENS = 1_200
SUMMARY_TOKENS = 450
WORKER_CALLS = {"search": 3, "rules": 3, "refund": 3, "hotel": 3,
                "notify": 2}
BRIEF_LOSS = 0.022       # a brief drops a fact the worker needed
LEAD_CATCH = 0.40        # the lead's check notices the missing fact
MERGE_ERROR = 0.012
WORKER_LEG_PENALTY = 0.004


@dataclass
class Run:
    ok: bool
    stopped: bool
    calls: int
    tokens: int
    coordination: int
    seconds: float


def _context_tokens(calls: int, start: int) -> int:
    return sum(start + CONTEXT_GROWTH * i for i in range(calls)) \
        + OUT_PER_CALL * calls


def single(case: Case, rng) -> Run:
    per_leg = LEG_CALLS if TYPES[case.kind][4] else 1
    extra = case.legs - 1
    calls = (BASE_CALLS[case.kind] + per_leg * extra
             + 3 * max(0, case.legs - 2) ** 2 + rng.randint(-1, 2))
    if calls > CALL_CAP:
        tokens = _context_tokens(CALL_CAP, SYSTEM_TOKENS)
        return Run(False, True, CALL_CAP, tokens, 0,
                   CALL_CAP * SECONDS_PER_CALL)
    p = QUALITY[case.kind] - LEG_PENALTY * extra
    return Run(rng.random() < p, False, calls,
               _context_tokens(calls, SYSTEM_TOKENS), 0,
               calls * SECONDS_PER_CALL)


def workers_for(case: Case) -> list[str]:
    _, _, _, specialists, per_leg = TYPES[case.kind]
    legs = ["search"] * case.legs if per_leg else []
    return legs + list(specialists)


def orchestrated(case: Case, rng) -> Run:
    ws = workers_for(case)
    w_calls = [WORKER_CALLS[w] + (rng.random() < 0.25) for w in ws]
    calls = LEAD_CALLS + sum(w_calls)
    # Coordination: plan and briefs written by the lead, each worker's
    # own system prompt and brief, summaries written and read back.
    briefs_out = BRIEF_TOKENS * len(ws)
    worker_overhead = sum((WORKER_SYSTEM + BRIEF_TOKENS) * c
                          for c in w_calls)
    summaries = 2 * SUMMARY_TOKENS * len(ws)
    lead_ctx = SYSTEM_TOKENS + LEAD_EXTRA + 1_500
    lead = sum(lead_ctx + SUMMARY_TOKENS * len(ws) * (i >= 1)
               for i in range(LEAD_CALLS)) + OUT_PER_CALL * LEAD_CALLS
    work = sum(_context_tokens(c, 0) for c in w_calls)
    coordination = briefs_out + worker_overhead + summaries \
        + SUMMARY_TOKENS * len(ws) * (LEAD_CALLS - 1)
    tokens = lead + work + worker_overhead + briefs_out + summaries
    seconds = (LEAD_CALLS + max(w_calls)) * SECONDS_PER_CALL
    if calls > CALL_CAP:
        return Run(False, True, calls, tokens, coordination, seconds)
    p = QUALITY[case.kind] - WORKER_LEG_PENALTY * (case.legs - 1)
    lost = sum(rng.random() < BRIEF_LOSS * (1 - LEAD_CATCH) for _ in ws)
    ok = rng.random() < p and lost == 0 and rng.random() > MERGE_ERROR
    return Run(ok, False, calls, tokens, coordination, seconds)


@dataclass
class TypeResult:
    kind: str
    n: int = 0
    single_ok: int = 0
    ow_ok: int = 0
    only_single: int = 0
    only_ow: int = 0
    single_tokens: int = 0
    ow_tokens: int = 0
    coordination: int = 0
    single_stops: int = 0
    ow_stops: int = 0
    many_leg_gain: int = 0     # (ow - single) on cases of 3+ legs
    few_leg_gain: int = 0      # (ow - single) on cases of 1-2 legs
    single_secs: list[float] = field(default_factory=list)
    ow_secs: list[float] = field(default_factory=list)

    @property
    def diff(self) -> float:
        return (self.ow_ok - self.single_ok) / self.n

    @property
    def se(self) -> float:
        d = self.only_single + self.only_ow
        return math.sqrt(d) / self.n if d else 0.0

    def per_outcome(self, tokens: int, ok: int) -> float:
        return tokens / ok if ok else float("inf")

    @property
    def winner(self) -> str:
        if abs(self.diff) > 2 * self.se and self.diff != 0:
            return "orchestrator" if self.diff > 0 else "single"
        s = self.per_outcome(self.single_tokens, self.single_ok)
        o = self.per_outcome(self.ow_tokens, self.ow_ok)
        return "tie-single" if s <= o else "tie-orchestrator"


@dataclass
class Bucket:
    n: int = 0
    single_ok: int = 0
    ow_ok: int = 0
    single_tokens: int = 0
    ow_tokens: int = 0


BUCKETS: dict[str, Bucket] = {}


def compare(seed: int = 27, cases: list[Case] | None = None,
            call_cap: int | None = None) -> dict[str, TypeResult]:
    """Per type results. Leg buckets ("1-2 legs", "3+ legs") are left
    in BUCKETS for the routing arithmetic in `routed`."""
    global CALL_CAP
    saved = CALL_CAP
    if call_cap is not None:
        CALL_CAP = call_cap
    try:
        cases = cases if cases is not None else golden_set(seed)
        out: dict[str, TypeResult] = {}
        BUCKETS.clear()
        for c in cases:
            b = BUCKETS.setdefault("3+ legs" if c.legs >= 3
                                   else "1-2 legs", Bucket())
            r = out.setdefault(c.kind, TypeResult(c.kind))
            for rep in range(REPEATS):
                s = single(c, seeded(seed, "single", c.case_id, str(rep)))
                o = orchestrated(c, seeded(seed, "ow", c.case_id,
                                           str(rep)))
                r.n += 1
                r.single_ok += s.ok
                r.ow_ok += o.ok
                r.only_single += s.ok and not o.ok
                r.only_ow += o.ok and not s.ok
                r.single_tokens += s.tokens
                r.ow_tokens += o.tokens
                r.coordination += o.coordination
                r.single_stops += s.stopped
                r.ow_stops += o.stopped
                gain = int(o.ok) - int(s.ok)
                if c.legs >= 3:
                    r.many_leg_gain += gain
                else:
                    r.few_leg_gain += gain
                b.n += 1
                b.single_ok += s.ok
                b.ow_ok += o.ok
                b.single_tokens += s.tokens
                b.ow_tokens += o.tokens
                r.single_secs.append(s.seconds)
                r.ow_secs.append(o.seconds)
        return out
    finally:
        CALL_CAP = saved


def p95(xs: list[float]) -> float:
    xs = sorted(xs)
    return xs[max(0, math.ceil(0.95 * len(xs)) - 1)]


def totals(res: dict[str, TypeResult]) -> dict:
    n = sum(r.n for r in res.values())
    st = sum(r.single_tokens for r in res.values())
    ot = sum(r.ow_tokens for r in res.values())
    co = sum(r.coordination for r in res.values())
    wins = [r.winner for r in res.values()]
    return {"runs": n,
            "single_ok": sum(r.single_ok for r in res.values()) / n,
            "ow_ok": sum(r.ow_ok for r in res.values()) / n,
            "token_ratio": ot / st,
            "coordination_share": co / ot,
            "single_tokens_per_task": st / n,
            "ow_tokens_per_task": ot / n,
            "single_wins": sum(w in ("single", "tie-single")
                               for w in wins),
            "single_clear": wins.count("single"),
            "ties": sum(w.startswith("tie") for w in wins),
            "ow_wins": sum(w in ("orchestrator", "tie-orchestrator")
                           for w in wins)}


def routed() -> dict:
    """Route by legs: three or more to orchestrator-worker, the rest to
    one agent. Uses the buckets of the last `compare` call."""
    few, many = BUCKETS["1-2 legs"], BUCKETS["3+ legs"]
    n = few.n + many.n
    single_tok = few.single_tokens + many.single_tokens
    return {"runs": n,
            "many_leg_runs": many.n,
            "all_single_ok": (few.single_ok + many.single_ok) / n,
            "all_ow_ok": (few.ow_ok + many.ow_ok) / n,
            "routed_ok": (few.single_ok + many.ow_ok) / n,
            "routed_token_ratio": (few.single_tokens + many.ow_tokens)
            / single_tok,
            "few": few, "many": many}
