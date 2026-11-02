"""The router: a table from step to route, built from gate results.

Routing lives in the control plane, as data a person can read, and not
in the gateway, which carries calls and does not choose models. The
table is rebuilt only from evidence: the risk class sets a floor, the
gate says which candidates pass, and the cheapest passing candidate at
or above the floor wins. Two rules exist only to be compared with it:
`frontier`, which is April's configuration, and `cost-only`, which
picks the cheapest candidate and never reads the gate.
"""
from __future__ import annotations

from dataclasses import dataclass

from .budget import TIERS, Candidate, cap
from .gate import Gate
from .steps import Step

RULES = ("frontier", "gated", "cost-only")


@dataclass(frozen=True)
class Route:
    step: str
    label: str                 # small, mid@high, small>frontier, ...
    reason: str
    evidence: str

    @property
    def cascade(self) -> tuple[str, str] | None:
        if ">" in self.label:
            a, b = self.label.split(">")
            return a, b
        return None

    @property
    def first(self) -> Candidate:
        lab = self.cascade[0] if self.cascade else self.label
        return Candidate.parse(lab)


def _ev(g: Gate) -> str:
    return f"{g.passed}/{g.total} ${g.mean_usd:.4f} p95 {g.p95_s:.1f}s"


def decide(steps: dict[str, Step], gates: dict[str, list[Gate]],
           rule: str = "gated", max_effort: str = "high"
           ) -> dict[str, Route]:
    if rule not in RULES:
        raise ValueError(rule)
    table = {}
    for name, step in steps.items():
        gs = gates[name]
        if rule == "frontier":
            g = next((x for x in gs if x.label == "frontier"), None)
            table[name] = Route(name, "frontier", "april config",
                                _ev(g) if g else "not gated")
            continue
        if rule == "cost-only":
            g = min((x for x in gs if ">" not in x.label),
                    key=lambda x: x.mean_usd)
            table[name] = Route(name, g.label, "cheapest", _ev(g))
            continue
        floor = TIERS.index(step.floor)
        ok = []
        for g in gs:
            if not g.ok or g.tier < floor:
                continue
            first = g.label.split(">")[0]
            try:
                cap(Candidate.parse(first), max_effort)
            except ValueError:
                continue
            ok.append(g)
        if not ok:
            table[name] = Route(name, "person", "no candidate passed", "")
            continue
        g = min(ok, key=lambda x: (x.mean_usd, x.p95_s))
        why = "cascade passed" if ">" in g.label else "cheapest passing"
        table[name] = Route(name, g.label, why, _ev(g))
    return table
