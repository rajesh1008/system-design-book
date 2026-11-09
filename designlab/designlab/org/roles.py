"""Seats on Daniel Price's platform team and the partners around it.

A seat is headcount on the team. A partner is a named person in
another function who holds decision rights the team depends on; a
partner is not headcount. Dates are the day a person can decide:
the first working day for a hire, None for someone already seated.
Skill levels run 0 (none) to 3 (can own it and teach it), assessed
by Daniel Price in the August review; the six skills are in
skills.py. Lakeshore figures are illustrative.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date

AS_OF = date(2026, 8, 31)


@dataclass(frozen=True)
class Seat:
    key: str            # short id used by the matrix
    title: str
    holder: str         # a name, or the role while the seat is new
    plane: str          # primary plane (or "all")
    team: str
    starts: date | None = None   # None: seated before the as-of date
    levels: tuple = ()  # six levels in SKILLS order

    def seated_on(self, day: date) -> bool:
        return self.starts is None or self.starts <= day


@dataclass(frozen=True)
class Person:
    key: str
    name: str
    function: str
    team: str
    holds: str          # what the partner decides, in a phrase


# SKILLS order: distributed, models, retrieval, control, evaluation,
# operations.
SEATS: tuple[Seat, ...] = (
    Seat("lead", "lead", "Daniel Price", "all",
         "platform", None, (3, 2, 2, 3, 2, 2)),
    Seat("architect", "agent systems architect",
         "agent systems architect", "all", "platform",
         date(2026, 9, 14), (2, 2, 2, 3, 2, 2)),
    Seat("agent1", "agent engineer", "agent engineer 1", "action",
         "platform", None, (2, 3, 2, 1, 1, 1)),
    Seat("agent2", "agent engineer", "agent engineer 2", "knowledge",
         "platform", None, (1, 2, 3, 0, 1, 1)),
    Seat("agent3", "agent engineer", "agent engineer 3", "action",
         "platform", None, (2, 2, 1, 1, 1, 1)),
    Seat("plat1", "platform engineer", "platform engineer 1",
         "control", "platform", None, (3, 0, 0, 2, 0, 2)),
    Seat("plat2", "platform engineer", "platform engineer 2",
         "control", "platform", None, (2, 1, 1, 1, 0, 2)),
    Seat("eval1", "evaluation engineer", "evaluation engineer 1",
         "trail", "platform", None, (1, 2, 1, 0, 3, 1)),
    Seat("eval2", "evaluation engineer", "evaluation engineer 2",
         "trail", "platform", date(2026, 9, 8), (1, 2, 1, 1, 3, 1)),
    Seat("sre1", "SRE", "Ben Carter", "trail", "platform",
         None, (3, 0, 0, 1, 1, 3)),
    Seat("sre2", "SRE", "Lena Okafor", "trail", "platform", None,
         (2, 0, 0, 1, 0, 3)),
)

# The June requisition the August review replaced (section 4).
JUNE_REQ = Seat("architect", "ML engineer, agents",
                "ML engineer, agents", "action", "platform",
                date(2026, 9, 14), (1, 3, 2, 0, 1, 1))

PARTNERS: tuple[Person, ...] = (
    Person("cto", "Sarah Whitfield", "chief technology officer",
           "exec", "budgets, the envelope, ties between owners"),
    Person("research", "Hannah Clarke", "applied research", "research",
           "the evaluation gate, golden sets, judge calibration"),
    Person("security", "Owen Fletcher", "security", "security",
           "scopes, the policy repository, threat models"),
    Person("redteam", "Imani Brooks", "security (deputy)", "security",
           "deputy for scopes and threat models"),
    Person("risk", "Rachel Morgan", "risk", "risk",
           "refund rules, risk tiers, audit evidence"),
    Person("risk2", "Elena Vasquez", "risk (deputy)", "risk",
           "deputy for refund rules and risk tiers"),
    Person("ops", "Marcus Bell", "operations", "ops",
           "rebook, voucher and credit rules; autonomy; customers"),
    Person("desk", "Keisha Navarro", "agent desk lead", "ops",
           "deputy for operations rules and messages"),
    Person("finance", "Priya Natarajan", "finance", "finance",
           "chargeback and the monthly bill review"),
)

# Role strings the matrix may name that are rotations, not people.
ROTATIONS = {
    "on-call primary": "platform",
    "on-call secondary": "platform",
    "operations duty manager": "ops",
    "loyalty product owner": "loyalty",
}


def seated(day: date = AS_OF, seats=SEATS) -> list[Seat]:
    return [s for s in seats if s.seated_on(day)]


def team_of(name: str, seats=SEATS, partners=PARTNERS) -> str | None:
    for s in seats:
        if name in (s.holder, s.key):
            return s.team
    for p in partners:
        if name == p.name:
            return p.team
    return ROTATIONS.get(name)


def available(name: str, day: date, seats=SEATS,
              partners=PARTNERS) -> str | None:
    """None if `name` can decide on `day`, else the reason."""
    for s in seats:
        if name in (s.holder, s.key):
            if s.seated_on(day):
                return None
            return f"seat starts {s.starts:%b} {s.starts.day}"
    if any(p.name == name for p in partners) or name in ROTATIONS:
        return None
    return "not on the roster"
