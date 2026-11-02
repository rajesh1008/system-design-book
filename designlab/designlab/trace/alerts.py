"""Alerts that mean something.

An alert is worth a page when it names something a customer, an
auditor or the budget would notice, has an owner, and says what the
owner does. Everything else is a dashboard. The noise rules below are
the ones the pilot had: each fires on an ordinary day.
"""
from __future__ import annotations

import json
from dataclasses import dataclass

from durable.bench import pct

from . import complete, conventions as c
from .cost import decisions


@dataclass(frozen=True)
class Rule:
    name: str
    metric: str
    threshold: float
    owner: str
    action: str
    pages: bool = True


RULES = (
    Rule("trace incomplete", "incomplete_runs", 0, "Ben Carter",
         "freeze the release"),
    Rule("effect not verified", "unverified_effects", 0, "Marcus Bell",
         "desk rechecks each refund"),
    Rule("reads refused > 5%", "refused_read_share", 0.05,
         "Daniel Price", "tier one: tool off"),
    Rule("cost/decision p95 > $0.12", "cost_per_decision_p95", 0.12,
         "Daniel Price", "diff cache, prompt by version"),
    Rule("hand-offs > 8%", "handoff_share", 0.08, "Marcus Bell",
         "staff desk; read the stops"),
)

NOISE = (
    Rule("call latency p95 > 1.5 s", "call_ms_p95", 1500, "-",
         "-", pages=False),
    Rule("any tool error", "tool_errors", 0, "-", "-", pages=False),
    Rule("tokens/call p95 > 8,000", "tokens_p95", 8000, "-", "-",
         pages=False),
)


def metrics(fl) -> dict:
    rep = complete.fleet_report(fl)
    lines = [json.loads(x) for x in fl.gateway.trail.lines]
    reads = [x for x in lines if x["tool"] not in
             ("refund_ticket", "customer_notify", "handoff_to_desk")]
    unverified, costs, call_ms, toks, errors = 0, [], [], [], 0
    for r in fl.results:
        ds = decisions(r.trace, r.evidence)
        costs += [float(d["usd"]) for d in ds]
        for s in r.trace:
            if s.name.startswith("verify ") and \
                    s.attrs.get(c.VERIFY_RESULT) != "match":
                unverified += 1
            if s.name.startswith(("chat ", "execute_tool ")):
                call_ms.append(s.ms)
            if s.name.startswith("chat "):
                toks.append(s.attrs[c.IN_TOKENS])
            if s.status == "ERROR":
                errors += 1
    unverified += sum(1 for f in rep["failed"] for p in f.problems
                      if p.endswith("no verify span"))
    n = len(fl.results)
    return {
        "runs": n,
        "incomplete_runs": len(rep["failed"]),
        "unverified_effects": unverified,
        "refused_read_share": sum(x["verdict"] == "refused"
                                  for x in reads) / max(1, len(reads)),
        "cost_per_decision_p95": pct(costs, 95),
        "handoff_share": sum(r.outcome == "handed_off"
                             for r in fl.results) / n,
        "call_ms_p95": pct(call_ms, 95),
        "tool_errors": errors,
        "tokens_p95": pct(toks, 95),
    }


def evaluate(m: dict, rules=RULES + NOISE) -> list[tuple[Rule, bool]]:
    return [(r, m[r.metric] > r.threshold) for r in rules]
