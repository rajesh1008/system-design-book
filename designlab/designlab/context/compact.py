"""Compaction: what happens to the history when a step would pass the
trigger, and a verifier that checks a summary against the trail.

Four policies, replayed over the same runs with the same random draws:

  none      keep everything; the context grows with the run
  truncate  drop the oldest history until the step fits the budget
  summary   a free-form summary replaces all but the last two steps;
            a later compaction summarizes the summary
  pinned    clear old tool results first (a stub with a re-fetch
            handle stays); if that is not enough, write a structured
            summary re-derived from the trail, never from the last
            summary; carry the pinned facts verbatim from the run store

The free-form summary's losses are simulated with per-fact keep rates;
the live lab (`models.compaction`) measures them on a real model.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field

from common.rand import seeded
from common.trail import TrailWriter

from .assemble import Assembled, assemble, reuse
from .rot import success_at
from .runs import Fact, Run
from .slots import Budget, Item, clock_item, stable_items

POLICIES = ("none", "truncate", "summary", "pinned")
KEEP_STEPS = 2              # steps kept verbatim after a compaction
STUB_TOKENS = 30            # a cleared tool result: handle and one line
PIN_TOKENS = 40             # one pinned fact, verbatim
KEEP_RATE = {"constraint": 0.98, "approval": 0.97, "amount": 0.96,
             "idem": 0.95}
PENALTY = {"summary": 0.006, "pinned": 0.002}   # per compaction
FATAL = {"approval": 1.0, "idem": 1.0, "constraint": 0.7,
         "amount": 0.5}


@dataclass
class Result:
    run_id: str
    length: int
    policy: str
    tokens: list[int] = field(default_factory=list)   # per step
    compactions: int = 0
    lost: list[str] = field(default_factory=list)      # fact kinds
    second_card: bool = False      # a pending approval filed again
    alarms: list[str] = field(default_factory=list)
    success: bool = False
    reused: int = 0                # prefix tokens repeated step to step
    sent: int = 0                  # tokens sent across the run
    last: Assembled | None = None  # the final step, as assembled

    @property
    def peak(self) -> int:
        return max(self.tokens) if self.tokens else 0


@dataclass
class _Block:
    """History as the model sees it: per step, the items and the facts
    that are visible because those items are there."""
    step: int
    items: list[Item]
    facts: list[Fact]


def _summary_tokens(src: int, structured: bool) -> int:
    cap = 700 if structured else 900
    return min(cap, 250 + src // 12)


def replay(run: Run, policy: str, budget: Budget | None = None,
           seed: int = 21, trail: TrailWriter | None = None,
           alarms_on: bool = True, order=None,
           release: str = "v7") -> Result:
    budget = budget or Budget()
    if policy not in POLICIES:
        raise ValueError(policy)
    r = seeded(seed, "compact", policy, run.run_id)
    res = Result(run.run_id, run.length, policy)
    blocks: list[_Block] = []
    summary: _Block | None = None
    store: list[Fact] = []          # the run store keeps every fact
    prev: Assembled | None = None
    fatal_p = 0.0
    kw = {"order": order} if order else {}

    def parts(step):
        hist = ([*summary.items] if summary else []) + \
            [it for b in blocks for it in b.items]
        p = {"tools": [], "instructions": [], "policy": [],
             "examples": [], "task": run.task, "memory": run.memory,
             "history": hist, "retrieved": step.retrieved,
             "clock": [clock_item(f"{run.run_id}:{step.n}")]}
        for it in stable_items(release=release):
            p[it.slot].append(it)
        if policy == "pinned" and store:
            p["pinned"] = [Item("pinned", f.key, PIN_TOKENS,
                                text=f.text) for f in store]
        return p

    def visible() -> set[str]:
        keys = {f.key for b in blocks for f in b.facts}
        if summary:
            keys |= {f.key for f in summary.facts}
        if policy == "pinned":
            keys |= {f.key for f in store}
        return keys

    for step in run.steps:
        blocks.append(_Block(step.n, list(step.history), list(step.facts)))
        store.extend(step.facts)
        a = assemble(parts(step), budget, alarms_on=False, **kw)
        a0 = a.tokens
        if policy == "truncate" and a.tokens > budget.per_step:
            while a.tokens > budget.per_step and len(blocks) > 1:
                blocks.pop(0)
                a = assemble(parts(step), budget, alarms_on=False, **kw)
            res.compactions += 1
        elif policy in ("summary", "pinned") and a.tokens > budget.trigger:
            if policy == "pinned":
                for b in blocks[:-KEEP_STEPS]:
                    b.items = [it if not it.key.endswith(":tool") else
                               Item("history", it.key + ":stub",
                                    STUB_TOKENS)
                               for it in b.items]
                a = assemble(parts(step), budget, alarms_on=False, **kw)
            if a.tokens > budget.trigger and len(blocks) > KEEP_STEPS:
                old = blocks[:-KEEP_STEPS]
                src = sum(it.tokens for b in old for it in b.items)
                facts = [f for b in old for f in b.facts]
                if policy == "summary":
                    if summary:            # a summary of a summary
                        src += sum(i.tokens for i in summary.items)
                        facts = summary.facts + facts
                    facts = [f for f in facts
                             if r.random() < KEEP_RATE[f.kind]]
                    tok = _summary_tokens(src, structured=False)
                else:                      # re-derived from the trail
                    src += sum(i.tokens for i in summary.items) \
                        if summary else 0
                    tok = _summary_tokens(src, structured=True)
                    facts = []             # pinned slot carries them
                summary = _Block(0, [Item("history",
                                          f"{run.run_id}:summary",
                                          tok)], facts)
                blocks = blocks[-KEEP_STEPS:]
            res.compactions += 1
            if trail is not None and alarms_on:
                after = assemble(parts(step), budget, alarms_on=False,
                                 **kw).tokens
                trail.append({"event": "context.compacted",
                              "run": run.run_id, "step": step.n,
                              "policy": policy, "before": a0,
                              "after": after})
        a = assemble(parts(step), budget, trail=trail if alarms_on
                     else None, run=run.run_id, step=step.n,
                     alarms_on=alarms_on, **kw)
        res.alarms += a.alarms
        res.tokens.append(a.tokens)
        res.sent += a.tokens
        res.reused += reuse(prev, a)
        prev = a
        res.last = a
        missing = [k for k in step.needs if k not in visible()]
        for k in missing:
            kind = next(f.kind for f in store if f.key == k)
            if kind not in res.lost:
                res.lost.append(kind)
            fatal_p = max(fatal_p, FATAL[kind])
            if kind in ("approval", "idem"):
                res.second_card = True
    p = success_at(res.peak) * (1 - PENALTY.get(policy, 0.0)) ** \
        res.compactions
    u = seeded(seed, "outcome", run.run_id).random()
    f = seeded(seed, "fatal", run.run_id).random()
    res.success = u < p and not f < fatal_p
    return res


# The verifier. A summary is text a model wrote; the trail is what
# happened. Every pinned fact must appear in the summary or the pinned
# slot, and every identifier or amount in the summary must be in the
# trail.

IDENT = re.compile(r"\b(?:APR|LTG|TKT|FLT|PRM|TRV)-\d{4,8}\b"
                   r"|\$\d[\d,]*\.\d{2}|\bidem-[\w-]+")


def identifiers(text: str) -> set[str]:
    return set(IDENT.findall(text))


def verify_summary(summary: str, pinned: list[str],
                   trail_text: str) -> list[str]:
    """Findings, empty when the summary is safe to resume from."""
    found = []
    have = identifiers(summary)
    for fact in pinned:
        need = identifiers(fact) or {fact}
        for x in sorted(need):
            if x not in have and x not in summary:
                found.append(f"dropped {x}")
    known = identifiers(trail_text)
    for x in sorted(have - known):
        found.append(f"not in trail {x}")
    return found
