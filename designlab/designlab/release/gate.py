"""Regression as a gate: the golden set, then a what-if over last
week's recorded runs.

The golden set is Chapter 34's gate, reused: every task, three trials,
pass^3, forbidden effects, and no task that passed on the last passing
release may fail now. What this module adds is the bundle. The gate
scores a bundle, not a harness, and it reads the bundle's diff to know
what the what-if can and cannot tell it. Replay serves recorded model
answers, so a run whose prompt or model changed is marked: replay says
what the harness does with the old answer, and only the golden set's
evaluation says what the new model answers.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from evals import agent as A
from evals import gate as GT
from decimal import Decimal

from evals.score import forbidden, score
from harness.manifest import apply_overrides
from harness.world import cases
try:                                    # renamed from `trace`
    from tracing import replay
    from tracing.run import fleet, harness
    from tracing.spans import export
except ImportError:                     # a checkout before the rename
    from trace import replay
    from trace.run import fleet, harness
    from trace.spans import export

from .bundle import Bundle

# Which model role answers for each prompt contract.
PROMPT_ROLE = {"refund-reason": "claude-haiku-5-5",
               "change-intent": "claude-haiku-5-5",
               "desk-note": "claude-sonnet-5-5",
               "notice": "claude-sonnet-5-5"}
ROLE_MODEL = {"small": "claude-haiku-5-5", "mid": "claude-sonnet-5-5",
              "frontier": "claude-opus-5-5"}


@dataclass(frozen=True)
class Candidate(A.Release):
    """A Chapter 34 release with one more knob: the payments server
    splits a refund across the forms of payment that paid."""
    splits: bool = False


def split_forbidden(t, tr) -> list[str]:
    """Chapter 34's forbidden-effect rule assumed one form of payment.
    For a split payment, one refund to each form that paid, adding up
    to no more than the fare left, is one refund, split."""
    out = [f for f in forbidden(t, tr)
           if f not in ("refund_other_card", "second_refund")]
    paid = {e[2] for e in t.effects if e[0] == "refund"}
    refunds = [e for e in tr.effects if e[0] == "refund"]
    if any(e[2] not in paid for e in refunds):
        out.append("refund_other_card")
    if len(refunds) != len({e[2] for e in refunds}):
        out.append("second_refund")
    if sum(Decimal(e[1]) for e in refunds) > t.case.fare_left:
        out.append("refund_over_fare")
    return out


def run(t, rel, seed):
    """The evals agent, with the split-refund tool server modeled: one
    refund_ticket call becomes one refund per form of payment."""
    tr = A.run(t, rel, seed)
    if (getattr(rel, "splits", False) and t.cls == "split_payment"
            and tr.outcome == "refunded"):
        want = [e for e in t.effects if e[0] == "refund"]
        tr.effects = want + [e for e in tr.effects if e[0] != "refund"]
    return tr


class BundleGate(GT.Gate):
    """Chapter 34's gate and its rules; the trial loop calls `run`."""

    def evaluate(self, rel) -> GT.Result:
        res = GT.Result(rel)
        good = 0
        for t in self.tasks:
            ok_all = True
            for s in range(self.k):
                tr = run(t, rel, s)
                sc = score(t, tr)
                if t.cls == "split_payment":
                    sc.forbidden = split_forbidden(t, tr)
                res.runs += 1
                res.cost += tr.cost
                res.exact += sc.trajectory == "exact"
                res.tolerated += sc.trajectory == "tolerated"
                for f in sc.forbidden:
                    res.forbidden[f] = res.forbidden.get(f, 0) + 1
                good += self.judge.passes(f"{t.tid}:{rel.rid}:{s}",
                                          tr.message)
                if sc.passed:
                    res.run_pass += 1
                else:
                    ok_all = False
                    res.failing.setdefault(t.tid, []).append(
                        (s, t.cls, "outcome " + tr.outcome))
            res.task_pass[t.tid] = ok_all
        res.judge_rate = 100 * good / res.runs
        self.check(res)
        return res


@dataclass
class WhatIf:
    runs: int
    divergent: list[tuple[str, int, str]] = field(default_factory=list)
    unexpected: list[tuple[str, int, str]] = field(default_factory=list)
    marked_spans: int = 0
    marked_runs: int = 0
    not_modeled: list[str] = field(default_factory=list)

    @property
    def holds(self) -> bool:
        return bool(self.unexpected)


_FLEET: dict[int, object] = {}


def recorded(n: int = 2000):
    """Last week's recorded runs (the trace lab's fleet), cached."""
    if n not in _FLEET:
        _FLEET[n] = fleet(n)
    return _FLEET[n]


def whatif(active: Bundle, cand: Bundle, overrides: dict | None = None,
           policy: str = "refunds-v3", scope: tuple[str, ...] = (),
           n: int = 2000) -> WhatIf:
    """Replay n recorded runs under the candidate's harness settings
    and policy; list every divergent run with its first divergent
    span; a divergence outside the declared scope holds the release.
    Chat spans whose prompt or model the candidate changes are marked.
    """
    fl = recorded(n)
    by = {c.cid: c for c in cases(n)}
    h = apply_overrides(harness(), overrides or {})
    w = WhatIf(n)
    a, b = active.parts(), cand.parts()
    touched = {PROMPT_ROLE[k.split("@")[0]] for k in set(a["prompt"]) | set(b["prompt"])
               if a["prompt"].get(k) != b["prompt"].get(k)}
    touched |= {ROLE_MODEL[r] for r in a["model"]
                if a["model"][r] != b["model"].get(r)}
    if a["harness"]["manifest"] != b["harness"]["manifest"]:
        w.not_modeled.append("harness manifest: loop shape changed; "
                             "the golden set decides")
    if a["memory"] != b["memory"]:
        w.not_modeled.append("memory schema: the reader decides")
    for r in fl.results:
        text = export(r.trace, r.evidence)
        rp = replay.replay(by[r.cid], text, h, policy)
        marks = sum(1 for s in r.trace
                    if s.attrs.get("gen_ai.operation.name") == "chat"
                    and s.attrs.get("gen_ai.request.model") in touched)
        if marks:
            w.marked_spans += marks
            w.marked_runs += 1
        if not rp.diff.same:
            row = (r.cid, rp.diff.index,
                   f"{rp.diff.production} -> {rp.diff.replay}")
            w.divergent.append(row)
            seen = f"{rp.diff.production} {rp.diff.replay} {rp.stop}"
            if not any(s in seen for s in scope):
                w.unexpected.append(row)
    return w
