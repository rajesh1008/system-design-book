"""The completeness check: is this trace the whole run?

A trace cannot prove its own completeness; a missing span leaves no
gap you can see from inside. So the check compares the trace with a
record written by something else: the gateway's trail, which writes a
line for every tool call that passes through it whether or not anyone
made a span. Then it checks the chain inside the trace: every effect
that succeeded has a permit from a policy span before it and a verify
span after it, and every span hangs off a parent that exists.
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field

from . import conventions as c
from .spans import Span


@dataclass
class Report:
    run: str
    steps: int = 0
    steps_traced: int = 0
    calls: int = 0
    calls_traced: int = 0
    problems: list[str] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return not self.problems


def check(run: str, spans: list[Span], trail_lines: list[str],
          conventions: bool = True) -> Report:
    rep = Report(run)
    ids = {s.span_id for s in spans}
    roots = [s for s in spans if s.parent_id is None]
    if len(roots) != 1:
        rep.problems.append(f"{len(roots)} root spans, want 1")
    for s in spans:
        if s.parent_id is not None and s.parent_id not in ids:
            rep.problems.append(f"orphan span {s.name}")
        if conventions:
            rep.problems += c.check_span(s)

    # steps: the root says how many there were; each needs a span
    want = roots[0].attrs.get(c.STEPS, 0) if roots else 0
    have = {s.attrs[c.STEP] for s in spans if s.name.startswith("step ")}
    rep.steps, rep.steps_traced = want, len(have & set(range(1, want + 1)))
    for n in sorted(set(range(1, want + 1)) - have):
        rep.problems.append(f"step {n} has no span")

    # every gateway line has a tool span with its call id, and back
    lines = [json.loads(x) for x in trail_lines]
    lines = [x for x in lines if x.get("run") == run]
    tools = {s.attrs.get(c.TOOL_CALL): s for s in spans
             if s.name.startswith("execute_tool ")}
    rep.calls = len(lines)
    for x in lines:
        if x["call"] in tools:
            rep.calls_traced += 1
        else:
            rep.problems.append(
                f"gateway call {x['call'][-2:]} {x['tool']}: no span")
    gw_calls = {x["call"] for x in lines}
    for cid, s in tools.items():
        if cid not in gw_calls:
            rep.problems.append(f"{s.name}: no gateway line")

    # the chain: permit before, verification after, trail link holds
    order = {s.span_id: i for i, s in enumerate(spans)}
    permits = {s.attrs.get(c.PERMIT): s for s in spans
               if s.name.startswith("policy ")
               and s.attrs.get(c.POLICY_VERDICT) == "permit"}
    verified = {s.attrs.get(c.VERIFY_OF) for s in spans
                if s.name.startswith("verify ")}
    for s in spans:
        if s.attrs.get(c.TOOL_KIND) != "effect":
            continue
        if s.attrs.get(c.VERDICT) != "allowed":
            continue
        name = s.attrs[c.TOOL_NAME]
        p = permits.get(s.attrs.get(c.PERMIT))
        if p is None or order[p.span_id] > order[s.span_id]:
            rep.problems.append(f"{name}: no policy span permits it")
        if s.attrs[c.TOOL_CALL] not in verified:
            rep.problems.append(f"{name}: no verify span")
        if s.attrs.get(c.TRAIL) is None:
            rep.problems.append(f"{name}: no trail link")
    return rep


def fleet_report(fl, **kw) -> dict:
    """Roll the check up over a fleet: steps and calls traced, and the
    runs that failed."""
    by_run: dict[str, list[str]] = {}
    for line in fl.gateway.trail.lines:
        by_run.setdefault(json.loads(line)["run"], []).append(line)
    reps = [check(r.cid, r.trace, by_run.get(r.cid, []), **kw)
            for r in fl.results]
    steps = sum(x.steps for x in reps)
    calls = sum(x.calls for x in reps)
    return {"runs": len(reps),
            "steps": steps,
            "steps_traced": sum(x.steps_traced for x in reps),
            "calls": calls,
            "calls_traced": sum(x.calls_traced for x in reps),
            "failed": [x for x in reps if not x.ok]}
