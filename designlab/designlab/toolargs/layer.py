"""The gateway intake: schema, then world, then a proposal (or not).

`Intake.check` returns a verdict. A passing verdict carries a digest of
the canonical arguments; the proposal, any approval card and the
redemption all name that digest, so a person who approves a call
approves those exact arguments (Section 5). `Tool` stands in for the
system of record's adapter and keeps its own log, which is how the
scorecard counts world-invalid calls that reached a tool without
trusting the intake's word for it.
"""
from __future__ import annotations

import hashlib
import json
from collections import Counter
from dataclasses import dataclass, field

from common.trail import TrailWriter

from . import schema
from .tools import TOOLS
from .world import World


def digest(tool: str, args: dict) -> str:
    raw = json.dumps({"tool": tool, "args": args}, sort_keys=True,
                     separators=(",", ":"))
    return hashlib.sha256(raw.encode()).hexdigest()[:12]


@dataclass
class Verdict:
    ok: bool
    stage: str | None          # "schema", "world" or None
    errors: list[dict]
    digest: str

    def for_model(self, repairs_left: int, bare: bool = False) -> dict:
        """What goes back to the model as the tool result."""
        if bare:
            return {"error": "invalid request"}
        return {"error": f"{self.stage}_rejected", "errors": self.errors,
                "repairs_left": repairs_left,
                "note": "fix the named field using the packet; "
                        "if you cannot, say so and stop"}


@dataclass
class Intake:
    world: World
    trail: TrailWriter
    mode: str = "full"              # or "schema-only"
    rules: tuple = ()
    counts: Counter = field(default_factory=Counter)
    reasons: Counter = field(default_factory=Counter)
    verdicts: dict = field(default_factory=dict)

    def check(self, session_itinerary: str, tool: str,
              args: dict) -> Verdict:
        self.counts["checked"] += 1
        d = digest(tool, args)
        spec = TOOLS.get(tool)
        if spec is None:
            v = Verdict(False, "schema", [{"field": "$", "problem":
                        "unknown tool"}], d)
        else:
            errs = schema.validate(args, spec["input_schema"])
            if errs:
                v = Verdict(False, "schema",
                            [e.as_dict() for e in errs], d)
            elif self.mode == "schema-only":
                v = Verdict(True, None, [], d)
            else:
                rej = self.world.check(tool, args, session_itinerary,
                                       self.rules)
                v = Verdict(rej is None, "world" if rej else None,
                            [rej.as_dict()] if rej else [], d)
        if v.stage != "schema":
            self.counts["schema_valid"] += 1
        if not v.ok:
            self.counts[f"{v.stage}_rejected"] += 1
            for e in v.errors:
                self.reasons[e.get("reason", e.get("problem"))] += 1
        else:
            self.counts["passed"] += 1
        self.verdicts[d] = v.ok
        self.trail.append({"kind": "intake", "tool": tool, "digest": d,
                           "session": session_itinerary, "ok": v.ok,
                           "stage": v.stage,
                           "reason": (v.errors[0].get("reason")
                                      if v.errors else None)})
        return v


@dataclass
class Tool:
    """The adapter on the far side of control. Logs what it receives."""
    world: World
    received: int = 0
    world_invalid: int = 0
    rejected_by_intake: int = 0
    wrong_ticket: int = 0
    over_fare_usd: float = 0.0

    def call(self, intake: Intake, session_itinerary: str, tool: str,
             args: dict) -> None:
        self.received += 1
        if intake.verdicts.get(digest(tool, args)) is False:
            self.rejected_by_intake += 1
        rej = self.world.check(tool, args, session_itinerary)
        if rej is not None:
            self.world_invalid += 1
            if rej.reason == "ticket_not_on_itinerary":
                self.wrong_ticket += 1
            if rej.reason == "amount_above_fare_left":
                t = self.world.tickets[args["ticket_number"]]
                self.over_fare_usd += float(args["amount_usd"]) - \
                    float(t.fare_left)
