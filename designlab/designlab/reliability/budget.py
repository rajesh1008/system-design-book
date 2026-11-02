"""Error budgets and the freeze rule (DR-37.1).

A budget is the bad events the target allows in its window. What a
budget is for is the rule attached to it, because a number nobody
acts on is a dashboard. Lakeshore's rule, per objective and per kind
of change where the objective is sliced:

  under half spent   releases ship as usual
  half spent         a release on that path needs the on-call lead's
                     sign-off and a written way back
  spent              freeze: only fixes and reliability work ship to
                     that path, and the path steps down one rung of
                     Chapter 12's ladder (full to propose-only) until
                     the 24-hour burn is under 1 and every unknown is
                     closed; the objective's owner restores it

A vendor's model change counts as a release: it spends the same
budget, and it is frozen out the same way, by pinning.

The unauthorized-actions objective has no budget to spend. One event
pulls tier two, freezes every release of the agent and the policy
bundle, and opens a review the security and risk owners close.
"""
from __future__ import annotations

from dataclasses import dataclass

from .objectives import Reading

RUNGS = ("full", "propose-only", "answer-only", "people-only")


@dataclass
class Decision:
    objective: str
    state: str          # ship, sign-off, freeze, stop
    rung: str
    why: str


def decide(r: Reading, rung: str = "full") -> Decision:
    if r.status == "unknown":
        return Decision(r.key, "sign-off", rung,
                        "no reading: treat as half spent, find the "
                        "records")
    if r.key.startswith("unauthorized"):
        if r.bad:
            return Decision(r.key, "stop", "propose-only",
                            f"{r.bad} unauthorized: tier two, freeze "
                            f"all")
        return Decision(r.key, "ship", rung, "zero")
    used = r.used or 0.0
    if used >= 1.0:
        down = RUNGS[min(RUNGS.index(rung) + 1, len(RUNGS) - 1)]
        return Decision(r.key, "freeze", down,
                        f"budget {used:.0%} spent: fixes only")
    if used >= 0.5:
        return Decision(r.key, "sign-off", rung,
                        f"budget {used:.0%} spent: sign-off")
    return Decision(r.key, "ship", rung, f"budget {used:.0%} spent")


def burn_down(daily_bad: list[int], budget: float) -> list[float]:
    """Remaining share of a window's budget after each day."""
    left, out = budget, []
    for b in daily_bad:
        left -= b
        out.append(left / budget if budget else 0.0)
    return out


def can_restore(burn_24h: float, open_unknowns: int,
                restorer: str, owner: str) -> tuple[bool, str]:
    if burn_24h >= 1.0:
        return False, f"24-hour burn {burn_24h:.1f}, not under 1"
    if open_unknowns:
        return False, f"{open_unknowns} unknowns open"
    if restorer != owner:
        return False, f"{restorer} is not the owner ({owner})"
    return True, "restore one rung"
