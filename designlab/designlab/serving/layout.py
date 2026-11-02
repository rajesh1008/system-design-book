"""Prompt layouts, and a linter that reads one before it ships.

A layout renders a call as an ordered list of segments plus the
positions of its cache breakpoints. The pilot layout is the one the
bake-off found: a timestamp and the itinerary ahead of the system
instructions. The stable-first layout puts everything that is the
same for every task of a kind first, then the task, then the clock.
"""
from __future__ import annotations

from dataclasses import dataclass

from .trace import (EXAMPLES, POLICY, SYSTEM, TIMESTAMP_TOKENS, TOOLS,
                    Call, Seg, Task, itinerary)

STABLE_PREFIXES = ("tools-", "instructions-", "examples-", "refunds-",
                   "changes-", "rebook-", "vouchers-")


@dataclass
class Rendered:
    segs: list[Seg]
    breakpoints: list[int]   # index of the last segment in each prefix
    ttls: tuple[float, ...] = ()   # seconds per breakpoint; 300 default

    @property
    def tokens(self) -> int:
        return sum(s.tokens for s in self.segs)


def history(task: Task, upto: int) -> list[Seg]:
    segs: list[Seg] = []
    for c in task.calls[:upto + 1]:
        segs.extend(c.new)
    return segs


def stamp(call: Call) -> Seg:
    return Seg(f"ts:{call.task}:{call.step}", TIMESTAMP_TOKENS)


def pilot(task: Task, call: Call) -> Rendered:
    """As found: one breakpoint on the last tool, the clock up top."""
    segs = [Seg(*TOOLS), stamp(call), itinerary(task, call), Seg(*SYSTEM),
            Seg(*POLICY[task.kind]), Seg(*EXAMPLES)]
    segs += history(task, call.step)
    return Rendered(segs, [0])


def stable_first(task: Task, call: Call) -> Rendered:
    """Stable first, task next, clock last; two breakpoints."""
    segs = [Seg(*TOOLS), Seg(*SYSTEM), Seg(*POLICY[task.kind]),
            Seg(*EXAMPLES)]
    bp1 = len(segs) - 1
    segs += [itinerary(task, call)] + history(task, call.step)
    bp2 = len(segs) - 1
    segs.append(stamp(call))
    return Rendered(segs, [bp1, bp2])


def clock_first(task: Task, call: Call) -> Rendered:
    """The try-it-yourself fault: a dynamic field ahead of the tools."""
    r = stable_first(task, call)
    segs = [stamp(call)] + r.segs[:-1]
    return Rendered(segs, [b + 1 for b in r.breakpoints])


LAYOUTS = {"pilot": pilot, "stable-first": stable_first,
           "clock-first": clock_first}


def is_stable(seg: Seg) -> bool:
    return seg.key.startswith(STABLE_PREFIXES)


def lint(r: Rendered) -> list[str]:
    """Findings: dynamic content ahead of stable content, and a
    breakpoint on a block whose prefix holds a per-call field."""
    found = []
    first_dyn = next((i for i, s in enumerate(r.segs)
                      if not is_stable(s)), len(r.segs))
    last_stable = max((i for i, s in enumerate(r.segs) if is_stable(s)),
                      default=-1)
    if last_stable > first_dyn:
        ahead = sum(s.tokens for s in r.segs[first_dyn:last_stable + 1]
                    if is_stable(s))
        found.append(f"dynamic {r.segs[first_dyn].key.split(':')[0]}"
                     f" at segment {first_dyn} sits ahead of"
                     f" {ahead:,} stable tokens")
    for b in r.breakpoints:
        if any(s.key.startswith("ts:") for s in r.segs[:b + 1]):
            found.append(f"breakpoint at segment {b} covers a"
                         " timestamp: every call writes, none reads")
    return found
