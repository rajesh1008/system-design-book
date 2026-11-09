"""Canaries by task type, measured on verified outcomes.

A canary sends a share of one task type's traffic to the candidate
bundle and the rest to the active bundle, then waits for the verdicts.
For refunds the verdict is the settlement file, which arrives daily,
so a stage cannot end before the file for its last day is in. At each
stage end the stop rule, fixed before the canary started, compares the
candidate's unverified outcomes with the control's: a one-sided exact
binomial tail below 0.01, or any forbidden effect, rolls the bundle
back. A latency-only canary watches p95 and cost instead.
Lakeshore figures are illustrative.
"""
from __future__ import annotations

import random
from dataclasses import dataclass, field
from math import exp, lgamma, log, log1p

# Daily volume by task type, late July 2026.
VOLUME = {"rebooking": 760, "refund": 200, "cancellation": 150,
          "credit": 120}
STAGES = (0.05, 0.25, 0.50, 1.00)
ALPHA = 0.01


def tail(x: int, n: int, p: float) -> float:
    """P(X >= x) for X ~ Binomial(n, p)."""
    if x <= 0:
        return 1.0

    def pmf(k: int) -> float:
        return exp(lgamma(n + 1) - lgamma(k + 1) - lgamma(n - k + 1)
                   + k * log(p) + (n - k) * log1p(-p))
    return max(0.0, min(1.0, sum(pmf(k) for k in range(x, n + 1))))


def p_detect(rate: float, n: int) -> float:
    """Chance that n runs show at least one instance of a defect that
    occurs once per 1/rate runs."""
    return 1 - (1 - rate) ** n


@dataclass
class Stage:
    share: float
    days: int
    runs: int = 0
    bad: int = 0
    ctrl_runs: int = 0
    ctrl_bad: int = 0
    p: float = 1.0
    p95_ms: int = 0
    ctrl_p95_ms: int = 0
    cost: float = 0.0
    ctrl_cost: float = 0.0
    forbidden: int = 0


@dataclass
class Canary:
    task_type: str
    stages: list[Stage] = field(default_factory=list)
    verdict: str = "running"

    @property
    def stopped_at(self) -> Stage | None:
        return self.stages[-1] if self.verdict == "rolled_back" else None


def run(task_type: str, cand_fail: float, ctrl_fail: float,
        days=(2, 1, 2), seed: int = 39, cand_ms=(9400, 2900),
        ctrl_ms=(14200, 4100), cand_cost=0.0088, ctrl_cost=0.0477,
        forbidden_rate: float = 0.0, measure: str = "verified",
        prior_days: int = 7) -> Canary:
    """Simulate a canary stage by stage. `measure` is "verified" (the
    stop rule above) or "latency" (p95 and cost no worse). Each stage
    end tests the candidate's runs so far against the control's runs
    so far plus the week before the canary started."""
    rng = random.Random(seed)
    c = Canary(task_type)
    vol = VOLUME[task_type]
    prior_n = prior_days * vol
    prior_bad = round(prior_n * ctrl_fail)
    n_cum = bad_cum = 0
    for share, d in zip(STAGES, days + (0,)):
        if share == 1.0:
            c.verdict = "full"
            break
        st = Stage(share, d)
        cl, kl = [], []
        for _ in range(d):
            for _ in range(vol):
                if rng.random() < share:
                    st.runs += 1
                    st.bad += rng.random() < cand_fail
                    st.forbidden += rng.random() < forbidden_rate
                    cl.append(max(800, rng.gauss(*cand_ms)))
                    st.cost += cand_cost
                else:
                    st.ctrl_runs += 1
                    st.ctrl_bad += rng.random() < ctrl_fail
                    kl.append(max(800, rng.gauss(*ctrl_ms)))
                    st.ctrl_cost += ctrl_cost
        cl.sort(), kl.sort()
        st.p95_ms = int(cl[int(0.95 * len(cl))])
        st.ctrl_p95_ms = int(kl[int(0.95 * len(kl))])
        n_cum += st.runs
        bad_cum += st.bad
        prior_n += st.ctrl_runs
        prior_bad += st.ctrl_bad
        st.p = tail(bad_cum, n_cum, max(prior_bad, 1) / prior_n)
        c.stages.append(st)
        if measure == "latency":
            worse = (st.p95_ms > st.ctrl_p95_ms
                     or st.cost / st.runs > st.ctrl_cost / st.ctrl_runs)
            if worse:
                c.verdict = "rolled_back"
                break
        elif st.p < ALPHA or st.forbidden:
            c.verdict = "rolled_back"
            break
    return c


def power(cand_fail: float, ctrl_fail: float, trials: int = 1000,
          task_type: str = "refund") -> dict:
    """Where simulated canaries stop: the stage share that rolled back,
    or "missed" when the bundle reached full exposure."""
    out: dict = {}
    for s in range(trials):
        c = run(task_type, cand_fail, ctrl_fail, seed=1000 + s)
        k = c.stages[-1].share if c.verdict == "rolled_back" else "missed"
        out[k] = out.get(k, 0) + 1
    return out


def pooled(cand_fail: float, ctrl_fail: float, share: float = 0.05,
           days: int = 3, seed: int = 39, defect_type: str = "refund"):
    """A canary over all traffic at once: the defect lives in one task
    type and is diluted by the others."""
    rng = random.Random(seed)
    n = bad = cn = cbad = 0
    for _ in range(days):
        for tt, vol in VOLUME.items():
            for _ in range(vol):
                f = cand_fail if tt == defect_type else ctrl_fail
                if rng.random() < share:
                    n += 1
                    bad += rng.random() < f
                else:
                    cn += 1
                    cbad += rng.random() < ctrl_fail
    return n, bad, cn, cbad, tail(bad, n, max(cbad, 1) / cn)
