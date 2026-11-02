"""The repair loop and its budget.

A rejected call goes back to the model with the verdict. Two rules keep
the loop finite and honest:

    budget       at most `budget` repairs (two by default); then the
                 case goes to the agent desk with the last verdict
    no progress  a repair that repeats the arguments it was given back
                 is not a repair; hand off at once

`budget=None` with `bare=True` reproduces the loop as it ran from May 12
to May 18, 2026: a bare "invalid request" and no cap but the framework's
own ceiling.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from .layer import Intake, Tool

CEILING = 50       # the framework's hard stop, only reached unbounded


@dataclass
class Outcome:
    status: str                  # passed, repaired, handed_off
    repairs: int
    model_calls: int
    reasons: list[str] = field(default_factory=list)
    why: str | None = None       # budget, no_progress, ceiling


def run_call(proposer, case, intake: Intake, tool: Tool,
             budget: int | None = 2, bare: bool = False) -> Outcome:
    sess, name = case.session, case.tool
    args = proposer.first(case)
    calls, reasons = 1, []
    v = intake.check(sess, name, args)
    repairs = 0
    while not v.ok:
        reasons.append((v.errors[0].get("reason")
                        or v.errors[0].get("problem")))
        limit = CEILING if budget is None else budget
        if repairs >= limit:
            why = "ceiling" if budget is None else "budget"
            return Outcome("handed_off", repairs, calls, reasons, why)
        left = (limit - repairs - 1)
        new = proposer.repair(case, args, v.for_model(left, bare))
        calls += 1
        repairs += 1
        if new == args and budget is not None:
            return Outcome("handed_off", repairs, calls, reasons,
                           "no_progress")
        args = new
        v = intake.check(sess, name, args)
    tool.call(intake, sess, name, args)
    return Outcome("repaired" if repairs else "passed", repairs, calls,
                   reasons)
