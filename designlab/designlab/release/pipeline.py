"""The release pipeline: bundle, gate, shadow, then A/B or canary by
task type, then full; and the deploy step that refuses anything else.

The deploy step is the one place a bundle becomes active, and it asks
three questions: is this a bundle the log knows, did it pass the gate
under this hash, and is the requested exposure allowed for the task
types the bundle touches. A prompt edited in a console fails the
first question, because its hash is in no record.
Lakeshore figures are illustrative.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from .bundle import Bundle, Record

# Task types and whether their effects can be taken back.
EFFECTS = {"rebooking": "booking", "refund": "money",
           "cancellation": "booking", "credit": "money",
           "notify": "none", "option_order": "none"}
ORDER = ("gate", "shadow", "ab", "canary", "full")


class Refused(Exception):
    pass


@dataclass
class Pipeline:
    records: dict[str, Record] = field(default_factory=dict)
    gated: dict[str, str] = field(default_factory=dict)   # hash -> rid
    active: dict[str, str] = field(default_factory=dict)  # type -> hash
    events: list[str] = field(default_factory=list)

    def submit(self, rec: Record) -> None:
        self.records[rec.bundle.hash] = rec

    def gate_passed(self, rec: Record, when: str) -> None:
        self.gated[rec.bundle.hash] = rec.rid
        rec.move(when, "gate")

    def plan(self, task_types: tuple[str, ...]) -> dict[str, tuple]:
        """Order of exposure per task type."""
        out = {}
        for t in task_types:
            if EFFECTS[t] == "none":
                out[t] = ("gate", "shadow", "ab", "full")
            else:
                out[t] = ("gate", "shadow", "canary", "full")
        return out

    def allow(self, method: str, task_type: str) -> None:
        if method == "bandit" and EFFECTS[task_type] != "none":
            raise Refused(f"bandit on {task_type}: effects are "
                          f"{EFFECTS[task_type]}; use a canary")
        if method == "ab" and EFFECTS[task_type] != "none":
            raise Refused(f"A/B on {task_type}: effects are "
                          f"{EFFECTS[task_type]}; use a canary")

    def deploy(self, b: Bundle, task_type: str, stage: str,
               share: float, when: str, method: str = "canary") -> str:
        rec = self.records.get(b.hash)
        if rec is None:
            raise Refused(f"bundle {b.hash} is in no release record")
        if b.hash not in self.gated:
            raise Refused(f"bundle {b.hash} ({rec.rid}) has no gate "
                          f"pass under this hash")
        self.allow(method, task_type)
        rec.move(when, stage)
        line = (f"{when} {rec.rid} {b.hash} {task_type} {stage} "
                f"{share:.0%}")
        self.events.append(line)
        if stage == "full":
            self.active[task_type] = b.hash
        return line

    def rollback(self, b: Bundle, task_type: str, when: str) -> str:
        rec = self.records[b.hash]
        rec.move(when, "rolled_back")
        parent = rec.parent
        self.active[task_type] = parent
        line = f"{when} {rec.rid} rolled back {b.hash} -> {parent}"
        self.events.append(line)
        return line
