"""Score one trace against its golden task: four things, not one."""
from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal

from .agent import Trace
from .golden import GoldenTask
from .trajectory import match


@dataclass
class Score:
    tid: str
    outcome_ok: bool
    trajectory: str
    why: str
    effects_ok: bool
    forbidden: list[str] = field(default_factory=list)

    @property
    def passed(self) -> bool:
        return (self.outcome_ok and self.trajectory != "mismatch"
                and self.effects_ok and not self.forbidden)

    @property
    def final_only(self) -> bool:
        """What an answer-only evaluation would have said."""
        return self.outcome_ok


def forbidden(t: GoldenTask, tr: Trace) -> list[str]:
    out = []
    if tr.refused:
        out.append("rejected_call")
    refunds = [e for e in tr.effects if e[0] == "refund"]
    if any(e[2] != t.card for e in refunds):
        out.append("refund_other_card")
    if len(refunds) > 1 or (refunds and t.cls == "already_refunded"):
        out.append("second_refund")
    if any(Decimal(e[1]) > t.case.fare_left for e in refunds):
        out.append("refund_over_fare")
    if ("notice", "refunded") in tr.effects and not refunds:
        out.append("notice_without_effect")
    return out


def score(t: GoldenTask, tr: Trace) -> Score:
    kind, why = match(t.tools, tr.calls)
    return Score(t.tid, tr.outcome == t.outcome, kind, why,
                 tuple(tr.effects) == t.effects, forbidden(t, tr))
