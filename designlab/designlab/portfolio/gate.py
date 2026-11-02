"""The gate: a candidate serves a step only if it passes the step's
golden set under the step's own limits.

The pass rule is the contract's, not the model's. Every case must meet
the contract and give the expected answer, the p95 latency must be
within the step's limit, and the mean cost per call within its
ceiling. A cascade is gated as a whole: the cases the verifier keeps on
the first model must be right there, and the cases it escalates must
be right on the second.
"""
from __future__ import annotations

from dataclasses import dataclass

from common.spend import SpendMeter

from models.contract import check, check_input, parse_json
from models.runner import (CaseResult, SuiteResult, _Spy, expectation)

from .budget import Candidate, client, contract_for
from .cascade import verify
from .steps import Step


def run_cases(step: Step, cand: Candidate, cases: list[dict], transport,
              meter: SpendMeter) -> SuiteResult:
    """First answers only, as in Chapter 13's run_suite, for one
    candidate of one step."""
    c = contract_for(step.contract, cand)
    spy = _Spy(transport)
    cl = client(c, cand, spy, meter)
    res = SuiteResult(c)
    for case in cases:
        inputs = case["input"]
        bad = check_input(c, inputs)
        if bad:
            res.cases.append(CaseResult(case["id"], "", bad, None, 0, 0))
            continue
        comp = cl.complete(c.render(inputs), system=c.system,
                           max_tokens=c.max_tokens)
        lat = (spy.last or {}).get("x_latency_ms", 0) / 1000
        obj = parse_json(comp.text)
        v = check(c, comp, inputs) + expectation(case, obj)
        res.cases.append(CaseResult(case["id"], comp.model, v, obj, lat,
                                    comp.cost_usd, comp.text))
    return res


@dataclass
class Gate:
    step: str
    label: str
    tier: int
    passed: int
    total: int
    p95_s: float
    mean_usd: float
    ok: bool
    escalated: int = 0
    failures: tuple[str, ...] = ()


def gate(step: Step, cand: Candidate, res: SuiteResult) -> Gate:
    n = len(res.cases)
    mean = res.cost_usd / n if n else 0.0
    ok = (res.passed == n and res.p95_s <= step.contract.p95_latency_s
          and mean <= step.contract.max_cost_usd)
    return Gate(step.name, cand.label, cand.tier, res.passed, n,
                res.p95_s, mean, ok,
                failures=tuple(r.case_id for r in res.cases
                               if not r.passed))


def cascade_gate(step: Step, first: SuiteResult, then: SuiteResult,
                 facts: dict[str, dict]) -> Gate:
    """Gate the cascade from the two candidates' recorded answers."""
    by_then = {r.case_id: r for r in then.cases}
    right, esc, cost, lat, fails = 0, 0, 0.0, [], []
    for r in first.cases:
        contract_v = [x for x in r.violations if x.code != "wrong-answer"]
        reasons = verify(step.name, r.output, contract_v,
                         facts.get(r.case_id, {}))
        cost += r.cost_usd
        if reasons:
            esc += 1
            t = by_then[r.case_id]
            cost += t.cost_usd
            lat.append(r.latency_s + t.latency_s)
            good = t.passed
        else:
            lat.append(r.latency_s)
            good = r.passed
        right += good
        if not good:
            fails.append(r.case_id)
    n = len(first.cases)
    lat.sort()
    p95 = lat[max(0, -(-95 * n // 100) - 1)] if lat else 0.0
    mean = cost / n if n else 0.0
    ok = (right == n and p95 <= step.contract.p95_latency_s
          and mean <= step.contract.max_cost_usd)
    a, b = step.cascade
    return Gate(step.name, f"{a}>{b}", Candidate(a).tier, right, n, p95,
                mean, ok, escalated=esc, failures=tuple(fails))
