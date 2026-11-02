"""Build the decision table from recorded gate runs."""
from __future__ import annotations

from common.spend import SpendMeter

from .gate import Gate, cascade_gate, gate, run_cases
from .budget import TIERS, Candidate
from .router import Route, decide
from .steps import Step, facts_for_golden, policy


def measure(step: Step, transport, meter: SpendMeter) -> dict:
    """Run the step's candidates in order. A "ladder" step stops at
    the first candidate at or above its floor that passes; the ones
    above it are not run, because nothing they show could change the
    route."""
    floor = TIERS.index(step.floor)
    runs = {}
    cases = step.cases()
    for c in step.candidates:
        runs[c.label] = run_cases(step, c, cases, transport, meter)
        if step.measure == "ladder" and c.tier >= floor \
                and gate(step, c, runs[c.label]).ok:
            break
    if step.cascade:
        for lab in step.cascade:
            if lab not in runs:
                c = Candidate.parse(lab)
                runs[lab] = run_cases(step, c, cases, transport, meter)
    return runs


def gates(steps: dict[str, Step], transport,
          meter: SpendMeter | None = None) -> dict[str, list[Gate]]:
    meter = meter if meter is not None else SpendMeter(cap_usd=5.0)
    out: dict[str, list[Gate]] = {}
    for name, step in steps.items():
        runs = measure(step, transport, meter)
        gs = [gate(step, c, runs[c.label]) for c in step.candidates
              if c.label in runs]
        if step.cascade:
            a, b = step.cascade
            facts = facts_for_golden() if name == "change-intent" else {}
            gs.append(cascade_gate(step, runs[a], runs[b], facts))
        out[name] = gs
    return out


def build(steps: dict[str, Step], transport, rule: str = "gated",
          meter: SpendMeter | None = None) -> dict[str, Route]:
    lim = policy()["limits"]
    return decide(steps, gates(steps, transport, meter), rule,
                  lim["max_effort"])
