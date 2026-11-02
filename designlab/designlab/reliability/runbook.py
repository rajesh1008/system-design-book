"""Runbooks as data, and the check every runbook passes.

A runbook is what the on-call engineer does in the first fifteen
minutes, written while nobody is paged. Each step names who acts,
what they act with, and the fact that shows the step worked; a step
whose check is "looks fine" is not a step. The stop step names its
tier and the far end whose count proves the stop, and the stop path
never runs through the thing that is failing. Lowering a tier is a
step of its own with a named person and a fresh decision.
"""
from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class Step:
    n: int
    who: str
    does: str
    using: str
    verify: str


@dataclass
class Runbook:
    key: str
    trigger: str
    stop_tier: int
    far_end: str
    steps: list[Step] = field(default_factory=list)
    never: list[str] = field(default_factory=list)
    release_by: tuple = ("Ben Carter", "Owen Fletcher")


VAGUE = ("looks fine", "check it", "monitor", "make sure", "as needed")


def lint(rb: Runbook, failing: str = "") -> list[str]:
    out = []
    if not rb.steps:
        out.append("no steps")
    for s in rb.steps:
        if not s.verify or any(v in s.verify.lower() for v in VAGUE):
            out.append(f"step {s.n}: no fact to verify")
        if not s.who:
            out.append(f"step {s.n}: nobody acts")
        if failing and failing in s.using and "tier" in s.does:
            out.append(f"step {s.n}: stop runs through {failing}")
    if not any(f"tier {_word(rb.stop_tier)}" in s.does for s in rb.steps):
        out.append(f"no step pulls tier {rb.stop_tier}")
    if not rb.far_end:
        out.append("stop has no far end to count")
    if not any("lower" in s.does for s in rb.steps):
        out.append("no step lowers the tier")
    return out


def _word(n: int) -> str:
    return {1: "one", 2: "two", 3: "three"}[n]


VENDOR = Runbook(
    "vendor-model-change",
    "verified outcomes page on one kind of change, no deploy",
    1, "bookings system count of reissues",
    [Step(1, "on-call", "acknowledge; post the objective, slice, burn",
          "pager, incident channel", "channel line with burn and time"),
     Step(2, "on-call", "read the deploy log and config history",
          "release log", "last change time written in the channel"),
     Step(3, "on-call", "pull tier one on the tool the slice acts with",
          "kill console (flag store)",
          "bookings count flat 20 s; held queue grows"),
     Step(4, "on-call", "read model echoes for the slice's steps",
          "model gateway records", "echo differs from pin: yes or no"),
     Step(5, "model owner", "pin the dated model; run the golden set",
          "model contract, golden runner", "golden set passes k of k"),
     Step(6, "desk lead", "work the held queue and the unverified",
          "desk queue", "every case owned, count to zero"),
     Step(7, "on-call", "lower the tier after a fresh decision",
          "kill console", "first effect verified by reconciler")],
    ["do not restart the agent", "do not reissue in bulk"])

STORM = Runbook(
    "loop-retry-storm",
    "provider count of a loop's calls pages, or latency with 429s",
    3, "provider count of the loop's calls",
    [Step(1, "on-call", "acknowledge; post the objective and burn",
          "pager, incident channel", "channel line with burn and time"),
     Step(2, "on-call", "find the key: calls by identity, last hour",
          "model gateway records", "top identity and its calls named"),
     Step(3, "on-call", "pull tier three on the loop identity",
          "kill console (flag store)",
          "provider count for the loop flat 20 s"),
     Step(4, "on-call", "confirm the shared limit has room again",
          "provider response headers", "429 share under 1% for 5 min"),
     Step(5, "loop owner", "list chains still queued; cancel them",
          "loop scheduler", "queued runs for the loop zero"),
     Step(6, "on-call", "lower the tier after a fresh decision",
          "kill console", "one run completes inside its budget")],
    ["do not pull tier two to stop spend: it holds effects only",
     "do not raise the rate limit"])

RUNBOOKS = (VENDOR, STORM)


def render(rb: Runbook) -> list[str]:
    out = [f"runbook {rb.key}", f"  when: {rb.trigger}",
           f"  stop: tier {rb.stop_tier}, counted at {rb.far_end}"]
    for s in rb.steps:
        out.append(f"  {s.n}. {s.who}: {s.does}")
        out.append(f"     check: {s.verify}")
    for n in rb.never:
        out.append(f"  never: {n}")
    out.append(f"  lowers a tier: {' or '.join(rb.release_by)}")
    return out


OLD = Runbook(
    "agent-incident (June)",
    "front door availability under 99.9%",
    2, "",
    [Step(1, "on-call", "acknowledge the page", "pager", "ack sent"),
     Step(2, "on-call", "check dashboards", "dashboards", "looks fine"),
     Step(3, "on-call", "pull tier two", "kill console", "monitor"),
     Step(4, "", "restart the agent service", "deploy tool",
          "service healthy")],
    [])
