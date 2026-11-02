"""The Release Gate: every release runs the Golden Set before it ships.

Each task runs k times. A release passes only if every task passes
all k trials (pass^k is 1.0), no forbidden effect happened in any
trial, nothing that passed on the last good release fails now, the
cost per task is within 10% of the last release, the exact-match rate
is within two points, and the wording judge is calibrated for its
current pin and scores no lower than two points under the last
release. Any failure blocks. An override is a record: who, why, what
they accepted, and it is never silent.
"""
from __future__ import annotations

import random
from dataclasses import dataclass, field
from decimal import Decimal

from . import agent as A
from . import golden as G
from . import judge as J
from .score import score

K = 3
COST_DRIFT = Decimal("0.10")
EXACT_DROP = 2.0
JUDGE_DROP = 2.0
CAN_OVERRIDE = ("Sarah Whitfield",)

# The nine releases the gate scored in June 2026, in order.
JUNE = (
    A.Release("R-0602", "2026-06-02", "memory-retention-v2", "memory"),
    A.Release("R-0603", "2026-06-03", "change-intent student, June "
              "retrain", "model"),
    A.Release("R-0605", "2026-06-05", "instruction file v10", "context"),
    A.Release("R-0609", "2026-06-09", "payments tool server: expired "
              "card falls back to card on file", "tool server",
              fallback_card=True),
    A.Release("R-0612", "2026-06-12", "payments tool server: fallback "
              "removed", "tool server"),
    A.Release("R-0617", "2026-06-17", "refund-reason, preference-tuned "
              "wording model", "model", reason_flip=0.05),
    A.Release("R-0619", "2026-06-19", "offers_search tool server "
              "patch", "tool server"),
    A.Release("R-0621", "2026-06-21", "tool servers on broker "
              "credentials", "identity"),
    A.Release("R-0623", "2026-06-23", "fare-rules extracts, waiver "
              "refresh", "knowledge"),
)
REHEARSAL = A.Release("R-0626", "2026-06-26", "harness 1.1.0: refunds "
                      "as a state machine", "harness",
                      manifest="servicing-1.1.0", shape="state_machine",
                      extra_read=0.0, swap_read=0.0)


@dataclass
class Result:
    rel: A.Release
    passed: bool = True
    reasons: list[str] = field(default_factory=list)
    failing: dict[str, list] = field(default_factory=dict)
    runs: int = 0
    run_pass: int = 0
    exact: int = 0
    tolerated: int = 0
    forbidden: dict[str, int] = field(default_factory=dict)
    regressions: list[str] = field(default_factory=list)
    cost: Decimal = Decimal("0")
    judge_rate: float = 0.0
    task_pass: dict[str, bool] = field(default_factory=dict)
    override: dict | None = None

    @property
    def pass1(self) -> float:
        return self.run_pass / self.runs

    @property
    def passk(self) -> float:
        return sum(self.task_pass.values()) / len(self.task_pass)

    @property
    def exact_pct(self) -> float:
        return 100 * self.exact / self.runs

    @property
    def cost_per_task(self) -> Decimal:
        return (self.cost / self.runs).quantize(Decimal("0.0001"))

    def block(self, why: str) -> None:
        self.passed = False
        self.reasons.append(why)


def held_out(n: int = 300, seed: int = 34):
    """Messages from sandbox runs of the June candidates, labeled by
    people on the desk: (key, message, wording label, effect label)."""
    tasks = G.build()
    pool = [(t, A.run(t, r, 0)) for r in JUNE[2:6] for t in tasks]
    rng = random.Random(seed)
    out = []
    for t, tr in rng.sample(pool, n):
        sc = score(t, tr)
        out.append((f"{tr.tid}:{tr.rid}", tr.message,
                    J.people_label(tr.message), sc.effects_ok
                    and not sc.forbidden))
    return out


def calibration(judge=None, labels: str = "people:desk") -> J.Calibration:
    judge = judge or J.OfflineJudge()
    items = held_out()
    marks = ([w for _, _, w, _ in items] if labels != judge.id else
             [judge.passes(k, m) for k, m, _, _ in items])
    return J.calibrate(judge, [(k, m) for k, m, _, _ in items], marks,
                       labels)


class Gate:
    def __init__(self, tasks=None, k: int = K, judge=None,
                 cal: J.Calibration | None = None):
        self.tasks = tasks if tasks is not None else G.build()
        self.k = k
        self.judge = judge or J.OfflineJudge()
        self.cal = cal if cal is not None else calibration(self.judge)
        self.last: Result | None = None
        self.log: list[str] = []

    def evaluate(self, rel: A.Release) -> Result:
        res = Result(rel)
        good = 0
        for t in self.tasks:
            ok_all = True
            for s in range(self.k):
                tr = A.run(t, rel, s)
                sc = score(t, tr)
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
                        (s, t.cls, sc.why or ("forbidden " + ",".join(
                            sc.forbidden) if sc.forbidden else
                            "outcome " + tr.outcome)))
            res.task_pass[t.tid] = ok_all
        res.judge_rate = 100 * good / res.runs
        self.check(res)
        return res

    def check(self, res: Result) -> None:
        if not self.cal.valid_for(self.judge):
            res.block(f"judge not calibrated for {self.judge.pin}")
        n_fail = sum(not v for v in res.task_pass.values())
        if n_fail:
            res.block(f"pass^{self.k} {res.passk:.3f}: {n_fail} tasks "
                      f"failed at least one trial")
        if res.forbidden:
            res.block("forbidden effects " + ", ".join(
                f"{k} {v}" for k, v in sorted(res.forbidden.items())))
        last = self.last
        if last is not None:
            reg = [tid for tid, ok in res.task_pass.items()
                   if last.task_pass.get(tid) and not ok]
            res.regressions = reg
            if reg:
                res.block(f"regression: {len(reg)} tasks passed on "
                          f"{last.rel.rid} and fail now")
            if res.cost_per_task > last.cost_per_task * (1 + COST_DRIFT):
                res.block(f"cost per task ${res.cost_per_task} against "
                          f"${last.cost_per_task}")
            if res.exact_pct < last.exact_pct - EXACT_DROP:
                res.block(f"exact match {res.exact_pct:.1f}% against "
                          f"{last.exact_pct:.1f}%")
            if res.judge_rate < last.judge_rate - JUDGE_DROP:
                res.block(f"wording {res.judge_rate:.1f}% against "
                          f"{last.judge_rate:.1f}%")

    def record(self, res: Result) -> str:
        verdict = "pass" if res.passed else "BLOCKED"
        line = (f"{res.rel.date} {res.rel.rid} {verdict} "
                f"pass^{self.k} {res.passk:.3f} exact {res.exact_pct:.0f}%")
        self.log.append(line)
        if res.passed:
            self.last = res
        return line

    def override(self, res: Result, by: str, why: str,
                 accepted: str) -> dict:
        """Ship a blocked release anyway, on the record, or not at all."""
        if res.passed:
            raise ValueError("nothing to override")
        if by not in CAN_OVERRIDE:
            raise PermissionError(f"{by} cannot override the gate")
        if not why.strip() or not accepted.strip():
            raise ValueError("an override records why and what it accepts")
        res.override = {"by": by, "why": why, "accepted": accepted,
                        "reasons": list(res.reasons)}
        self.log.append(f"{res.rel.date} {res.rel.rid} OVERRIDE by {by}: "
                        f"{why}")
        return res.override


def run_june(gate: Gate | None = None) -> tuple[Gate, list[Result]]:
    gate = gate or Gate()
    out = []
    for rel in JUNE:
        res = gate.evaluate(rel)
        gate.record(res)
        out.append(res)
    return gate, out


def registry_line(res: Result, gate: Gate) -> str:
    """What the gate would add to harness/releases.toml at a cut. The
    lab prints it; it never writes Chapter 25's registry."""
    hz = A.harness_for(res.rel.manifest)
    return (f'[[release]] version = "{hz.version}" hash = "{hz.hash}" '
            f'gate = "{res.rel.rid} pass^{gate.k} {res.passk:.3f}"')
