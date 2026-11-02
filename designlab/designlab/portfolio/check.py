"""The router check: forty tasks through a routing table.

Each task is three model steps. A task succeeds when every step's
final answer is the expected one. A step that ends with a person is
not a success, but it is not a wrong answer either, and the two are
counted apart, because a wrong answer is what reaches a customer.
Every routed call writes a trail line: step, route, model, effort,
and whether the cascade escalated and why.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from common.spend import SpendMeter

from models.contract import check, check_input, parse_json
from models.runner import _Spy, expectation

from .budget import Candidate, client, contract_for
from .cascade import verify
from .router import Route
from .steps import Step


@dataclass
class StepRun:
    task: str
    step: str
    model: str
    escalated: bool
    reasons: tuple[str, ...]
    outcome: str               # right, wrong, person
    cost_usd: float
    latency_s: float


@dataclass
class CheckResult:
    rule: str
    runs: list[StepRun] = field(default_factory=list)
    trail: list[dict] = field(default_factory=list)
    cascaded: tuple[str, ...] = ()

    def tasks(self) -> dict[str, list[StepRun]]:
        out: dict[str, list[StepRun]] = {}
        for r in self.runs:
            out.setdefault(r.task, []).append(r)
        return out

    @property
    def n_tasks(self) -> int:
        return len(self.tasks())

    @property
    def success(self) -> int:
        return sum(all(r.outcome == "right" for r in rs)
                   for rs in self.tasks().values())

    @property
    def wrong_tasks(self) -> int:
        return sum(any(r.outcome == "wrong" for r in rs)
                   for rs in self.tasks().values())

    @property
    def cost_per_task(self) -> float:
        return sum(r.cost_usd for r in self.runs) / max(1, self.n_tasks)

    def share_ending_on(self, role: str) -> float:
        return sum(r.model == role for r in self.runs) / len(self.runs)

    def cascade_runs(self) -> list[StepRun]:
        return [r for r in self.runs if r.step in self.cascaded]

    @property
    def escalation_rate(self) -> float:
        cr = self.cascade_runs()
        return sum(r.escalated for r in cr) / len(cr) if cr else 0.0

    def high_risk_on(self, steps: dict[str, Step], role: str) -> int:
        return sum(r.model == role and steps[r.step].risk == "high"
                   for r in self.runs)


def _call(step, cand, inputs, transport, meter):
    c = contract_for(step.contract, cand)
    if check_input(c, inputs):
        return c, None, ["input"], 0.0, 0.0
    spy = _Spy(transport)
    cl = client(c, cand, spy, meter)
    comp = cl.complete(c.render(inputs), system=c.system,
                       max_tokens=c.max_tokens)
    lat = (spy.last or {}).get("x_latency_ms", 0) / 1000
    obj = parse_json(comp.text)
    return c, obj, check(c, comp, inputs), comp.cost_usd, lat


def run_check(tasks: list[dict], steps: dict[str, Step],
              table: dict[str, Route], transport, rule: str,
              meter: SpendMeter | None = None) -> CheckResult:
    meter = meter if meter is not None else SpendMeter(cap_usd=5.0)
    res = CheckResult(rule)
    res.cascaded = tuple(n for n, r in table.items() if r.cascade)
    for t in tasks:
        for name, spec in t["steps"].items():
            step, route = steps[name], table[name]
            case = {"expect": spec["expect"]}
            cand = route.first
            _, obj, v, cost, lat = _call(step, cand, spec["input"],
                                         transport, meter)
            reasons: list[str] = []
            model = cand.role
            if route.cascade:
                reasons = verify(name, obj, v, t["facts"])
                if reasons:
                    then = Candidate.parse(route.cascade[1])
                    _, obj, v, c2, l2 = _call(step, then, spec["input"],
                                              transport, meter)
                    cost, lat, model = cost + c2, lat + l2, then.role
            if v:
                outcome, model = "person", "person"
            elif expectation(case, obj) and obj.get("needs_person"):
                outcome, model = "person", "person"
            elif expectation(case, obj):
                outcome = "wrong"
            else:
                outcome = "right"
            res.runs.append(StepRun(t["id"], name, model, bool(reasons),
                                    tuple(reasons), outcome, cost, lat))
            res.trail.append({"task": t["id"], "step": name,
                              "route": route.label, "model": model,
                              "effort": cand.effort,
                              "escalated": bool(reasons),
                              "why": list(reasons)})
    return res
