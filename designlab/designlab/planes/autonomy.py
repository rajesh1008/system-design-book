"""Autonomy as a design parameter: one level per task type, with a ceiling.

The ceiling comes from three scores the team can argue about in a review
(reversibility, value at risk, independent verifiability), not from how
capable the model seems. `check_autonomy` returns every row that runs
above its ceiling or is missing what its level needs. A row may sit above
its ceiling only with an override that names a signer and an expiry.
"""
from __future__ import annotations

import tomllib
from dataclasses import dataclass, field
from pathlib import Path

from .action import CUSTOMER_STATES

LEVELS = ("suggest", "act_with_approval", "act_and_notify",
          "act_unattended")
# How each level is counted on the scoreboard (Chapter 4 definitions).
SCOREBOARD_PATH = {"suggest": "person", "act_with_approval": "assisted",
                   "act_and_notify": "agent", "act_unattended": "agent"}
HERE = Path(__file__).parent


def ceiling(reversibility: int, value_at_risk: int, verifiable: int) -> str:
    if verifiable == 0:
        return "suggest"
    if reversibility == 0 or value_at_risk == 0:
        return "act_with_approval"
    if reversibility == 2 and value_at_risk == 2:
        return "act_unattended"
    return "act_and_notify"


@dataclass
class Row:
    task: str
    policy: str
    policy_cap_usd: float
    limit_usd: float
    reversibility: int
    value_at_risk: int
    verifiable: int
    level: str
    handoff: str
    receiver: str
    customer_sees: list[str]
    sync_wait_s: float = 0
    promise_minutes: int | None = None
    daily_budget_usd: float | None = None
    refuse_window_hours: int | None = None
    audit_sample: float | None = None
    override: dict = field(default_factory=dict)

    @property
    def ceiling(self) -> str:
        return ceiling(self.reversibility, self.value_at_risk,
                       self.verifiable)

    @property
    def path(self) -> str:
        return SCOREBOARD_PATH[self.level]


@dataclass
class AutonomyTable:
    version: str
    agent_identity: str
    rows: dict[str, Row]

    def row(self, task: str) -> Row:
        return self.rows[task]


def load_autonomy(path: Path | None = None, text: str | None = None
                  ) -> AutonomyTable:
    data = tomllib.loads(text if text is not None
                         else (path or HERE / "autonomy.toml").read_text())
    rows = {name: Row(task=name, **body)
            for name, body in data["task"].items()}
    return AutonomyTable(data["version"], data["agent_identity"], rows)


def check_autonomy(table: AutonomyTable) -> list[str]:
    problems = []
    for name, r in table.rows.items():
        if r.level not in LEVELS:
            problems.append(f"{name}: unknown level {r.level}")
            continue
        if LEVELS.index(r.level) > LEVELS.index(r.ceiling):
            o = r.override
            if not (o.get("signed_by") and o.get("expires")):
                problems.append(f"{name}: {r.level} above ceiling "
                                f"{r.ceiling}")
        if r.limit_usd > r.policy_cap_usd:
            problems.append(f"{name}: limit above policy cap")
        if r.level == "act_unattended":
            if not r.limit_usd or r.daily_budget_usd is None:
                problems.append(f"{name}: unattended without limits")
            if not r.audit_sample:
                problems.append(f"{name}: unattended without audit sample")
        if r.handoff not in ("sync", "async"):
            problems.append(f"{name}: hand-off {r.handoff}")
        if r.handoff == "sync" and not (r.sync_wait_s and r.promise_minutes):
            problems.append(f"{name}: sync hand-off without fallback")
        if r.handoff == "async" and not r.promise_minutes:
            problems.append(f"{name}: async hand-off without a promise")
        if not r.receiver or r.receiver == table.agent_identity:
            problems.append(f"{name}: no human receiver")
        bad = [s for s in r.customer_sees if s not in CUSTOMER_STATES]
        if bad:
            problems.append(f"{name}: customer state {bad[0]!r} not "
                            f"from the chain")
    return problems
