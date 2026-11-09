"""The board's verdict rule.

  decline  a failing item whose fix is a new box or arrow (shape);
  change   failing items whose fix is a value, an owner, a limit;
  approve  every item passes.

A changed design may not go live until its blocking conditions are
met; a declined design comes back as a new submission.
"""
from __future__ import annotations

from dataclasses import dataclass

from . import checklist
from .submission import Submission


@dataclass(frozen=True)
class Verdict:
    design: str
    outcome: str            # approve, change, decline
    passed: int
    total: int
    shape: tuple            # failing shape items
    blocking: tuple         # failing blocking items (value fixes)
    other: tuple            # failing non-blocking items

    @property
    def may_ship(self) -> bool:
        return not self.shape and not self.blocking


def decide(sub: Submission, items=None) -> Verdict:
    res = checklist.run(sub, items)
    bad = [r for r in res if not r.passed]
    shape = tuple(r.item.id for r in bad if r.item.shape)
    block = tuple(r.item.id for r in bad
                  if r.item.blocking and not r.item.shape)
    other = tuple(r.item.id for r in bad if not r.item.blocking)
    if shape:
        outcome = "decline"
    elif bad:
        outcome = "change"
    else:
        outcome = "approve"
    return Verdict(sub.name, outcome, len(res) - len(bad), len(res),
                   shape, block, other)
