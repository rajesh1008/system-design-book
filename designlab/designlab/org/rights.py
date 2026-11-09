"""The decision-rights matrix and the scenario checker (Chapter 41).

A decision has exactly one owner, a deputy, people consulted, and
people informed. A scenario names the decisions a real change needs.
The checker walks each scenario and fails it when a decision:

  1. is not in the matrix;
  2. has no owner, or more than one;
  3. has an owner who cannot decide on the scenario's day;
  4. has an owner on the author's team (or the author), where the
     decision must be independent of the author;
  5. is time-critical and has no deputy;
  6. signs a policy bundle and the owner holds no signing key;
  7. consults or informs someone not on the roster;
  8. shares one owner between the evaluation gate and the release.

Matrices are dated. 2026-08-04 is the state on the day rebook-v3 was
drafted; 2026-08-19 is the first draft Daniel Price ran with Rachel
Morgan; 2026-08-21 is the version DR-41.1 signed.
Lakeshore figures are illustrative.
"""
from __future__ import annotations

from dataclasses import dataclass, replace
from datetime import date

from .roles import PARTNERS, SEATS, available, team_of


@dataclass(frozen=True)
class Decision:
    key: str
    text: str
    owners: tuple = ()          # exactly one, or the check fails
    deputy: str | None = None
    consulted: tuple = ()
    informed: tuple = ()
    independent: str | None = None   # "team", "person" or None
    urgent: bool = False             # needs a deputy
    signs: bool = False              # owner must hold a bundle key


@dataclass(frozen=True)
class Scenario:
    key: str
    title: str
    day: date
    author: str
    author_team: str
    needs: tuple


@dataclass(frozen=True)
class Finding:
    scenario: str
    decision: str
    problem: str


MB, KN = "Marcus Bell", "Keisha Navarro"
RM, EV = "Rachel Morgan", "Elena Vasquez"
OF, IB = "Owen Fletcher", "Imani Brooks"
HC, DP = "Hannah Clarke", "Daniel Price"
BC, LO = "Ben Carter", "Lena Okafor"
SW, PN = "Sarah Whitfield", "Priya Natarajan"

SIGNED: tuple[Decision, ...] = (
    Decision("rules.ops", "change a rebooking, voucher or credit rule",
             (MB,), KN, (RM, PN), (DP, BC), "team", False, True),
    Decision("rules.refund", "change a refund rule",
             (RM,), EV, (MB,), (DP, BC), "team", False, True),
    Decision("rules.security", "change a security rule",
             (RM,), EV, (OF,), (DP,), "team", False, True),
    Decision("bundle.activate", "activate a signed bundle after shadow",
             (BC,), LO, (OF,), (MB, RM), "person"),
    Decision("gate", "certify a change at the evaluation gate",
             (HC,), "evaluation engineer 1", (DP,), (BC,), "team"),
    Decision("release", "release a change (canary and ramp)",
             (BC,), LO, (HC,), (MB,), "person"),
    Decision("tool.register", "register a tool in the registry",
             (DP,), "platform engineer 1", (OF, HC), (BC,), "person"),
    Decision("tool.scopes", "grant a tool's scopes at the broker",
             (OF,), IB, (RM,), (DP,), "team"),
    Decision("autonomy", "set a task type's autonomy level",
             (MB,), KN, (RM, DP), (BC,), "team"),
    Decision("stop", "pull a kill switch at any tier",
             ("on-call primary",), "on-call secondary", (),
             (MB, DP), None, True),
    Decision("message", "tell customers about an incident",
             (MB,), "operations duty manager", (RM,), (DP,), None,
             True),
    Decision("restore", "restore service after a stop",
             (BC,), LO, (MB,), (DP, RM), None, True),
    Decision("budget.loop", "raise a loop's day budget",
             (DP,), SW, (PN,), (BC,), "person", True),
    Decision("budget.envelope", "exceed the month's spend envelope",
             (SW,), DP, (PN,), (MB,), "person", True),
    Decision("usecase.accept", "accept a use case onto the platform",
             (DP,), BC, (OF, RM, HC), (SW,), "team"),
    Decision("usecase.tier", "classify a use case's risk tier",
             (RM,), EV, (OF,), (DP,), "team"),
    Decision("usecase.threat", "approve a use case's threat model",
             (OF,), IB, (RM,), (DP,), "team"),
    Decision("usecase.live", "take a use case live",
             ("loyalty product owner",), None, (MB, DP), (SW,)),
)


def _edit(base, **changes) -> tuple[Decision, ...]:
    """Copy `base`, replacing fields per decision key."""
    out = []
    for d in base:
        if d.key in changes:
            d = replace(d, **changes[d.key])
        out.append(d)
    return tuple(out)


DRAFT = _edit(SIGNED, **{
    "tool.register": {"owners": ("agent systems architect",)},
    "message": {"owners": (MB, RM), "consulted": ()},
    "usecase.tier": {"owners": ()},
})

AUG4 = _edit(SIGNED, **{"rules.ops": {"owners": (),
                                      "consulted": (RM,)}})

MATRICES = {"2026-08-04": AUG4, "2026-08-19": DRAFT,
            "2026-08-21": SIGNED}

# Who could sign bundles in the bundle store, by matrix date.
SIGNERS = {"2026-08-04": (RM,),
           "2026-08-19": (RM, EV, MB, KN),
           "2026-08-21": (RM, EV, MB, KN)}

D = date(2026, 8, 21)
SCENARIOS: tuple[Scenario, ...] = (
    Scenario("policy-change", "rebook-v3: fare difference $250 to $400",
             D, "policy engineer", "security",
             ("rules.ops", "bundle.activate")),
    Scenario("model-change", "classifier route: sonnet to haiku",
             D, "agent engineer 1", "platform", ("gate", "release")),
    Scenario("new-tool", "hotel hold for stranded travelers",
             D, "agent engineer 3", "platform",
             ("tool.register", "tool.scopes", "autonomy", "gate",
              "release")),
    Scenario("incident-stop", "duplicate rebookings at 2:00 a.m.",
             D, "none (the system)", "none",
             ("stop", "message", "restore")),
    Scenario("budget-breach", "waiver watch at its loop day",
             D, BC, "platform", ("budget.loop", "budget.envelope")),
    Scenario("new-use-case", "loyalty points assistant",
             D, "loyalty product owner", "loyalty",
             ("usecase.accept", "usecase.tier", "usecase.threat",
              "usecase.live")),
)

# The seventh is loyalty's partner points transfer (Chapter 41's worked
# example): it needs usecase.transfer, a key the August 21 matrix lacks.
# Chapter 42's review board signs that key on September 4, 2026.
SEVENTH = Scenario("partner-transfer",
                   "points transfer to a partner",
                   D, "loyalty product owner", "loyalty",
                   ("usecase.transfer", "usecase.accept",
                    "usecase.tier", "usecase.live"))


def check(s: Scenario, matrix=SIGNED, signers=SIGNERS["2026-08-21"],
          day: date | None = None, seats=SEATS,
          partners=PARTNERS) -> list[Finding]:
    day = day or s.day
    by_key = {d.key: d for d in matrix}
    out: list[Finding] = []

    def bad(key: str, problem: str) -> None:
        out.append(Finding(s.key, key, problem))

    for key in s.needs:
        d = by_key.get(key)
        if d is None:
            bad(key, "not in the matrix")
            continue
        if not d.owners:
            bad(key, "no owner")
            continue
        if len(d.owners) > 1:
            bad(key, "two owners: " + " and ".join(d.owners))
            continue
        owner = d.owners[0]
        why = available(owner, day, seats, partners)
        if why:
            bad(key, f"owner {owner}: {why}")
        if d.independent == "person" and owner == s.author:
            bad(key, f"owner {owner} is the author")
        if d.independent == "team" and (
                owner == s.author
                or team_of(owner, seats, partners) == s.author_team):
            bad(key, f"owner {owner} is on the author's team")
        if d.urgent and not d.deputy:
            bad(key, "time-critical with no deputy")
        if d.urgent and d.deputy and available(d.deputy, day, seats,
                                               partners):
            bad(key, f"deputy {d.deputy} cannot decide")
        if d.signs and owner not in signers:
            bad(key, f"owner {owner} holds no signing key")
        for role, names in (("consulted", d.consulted),
                            ("informed", d.informed)):
            for who in names:
                if available(who, day, seats, partners):
                    bad(key, f"{role} {who}: gone")
    gate, rel = by_key.get("gate"), by_key.get("release")
    if ("gate" in s.needs and "release" in s.needs and gate and rel
            and gate.owners and gate.owners == rel.owners):
        bad("gate+release",
            f"{gate.owners[0]} holds both gate and release")
    return out


def check_all(matrix=SIGNED, signers=SIGNERS["2026-08-21"],
              scenarios=SCENARIOS, day: date | None = None,
              seats=SEATS, partners=PARTNERS
              ) -> list[tuple[Scenario, list[Finding]]]:
    return [(s, check(s, matrix, signers, day, seats, partners))
            for s in scenarios]


def without(name: str, partners=PARTNERS, matrix=SIGNED):
    """Remove a partner, and their deputy role, from the roster."""
    gone = {name}
    p = next(x for x in partners if x.name == name)
    gone |= {x.name for x in partners
             if x.team == p.team and x.name != name}
    kept = tuple(x for x in partners if x.name not in gone)
    return kept, gone


def reassign(key: str, owner: str, matrix=SIGNED):
    return _edit(matrix, **{key: {"owners": (owner,)}})


def owners(matrix=SIGNED) -> dict[str, list[str]]:
    """Owner -> decision keys, for the one-page view."""
    out: dict[str, list[str]] = {}
    for d in matrix:
        for o in d.owners:
            out.setdefault(o, []).append(d.key)
    return out
