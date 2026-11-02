"""Build the decision table from recorded gate runs."""
from __future__ import annotations

from common.spend import SpendMeter

from .gate import Gate, cascade_gate, gate, run_cases
from .router import Route, decide
from .steps import Step, facts_for_golden, policy


def measure(step: Step, transport, meter: SpendMeter) -> dict:
    """Every candidate of the step, on the step's golden set."""
    cases = step.cases()
    return {c.label: run_cases(step, c, cases, transport, meter)
            for c in step.candidates}


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
    pol = policy()
    return decide(steps, gates(steps, transport, meter), rule,
                  pol["limits"]["max_effort"],
                  tuple(pol["verifier"]["required_below_mid"]))
