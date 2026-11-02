"""The release log, July 13 to August 31, 2026.

Daniel Price rebuilt the change log after the INC-5 review on Monday,
July 13: every source that can change what the servicing agent does,
not only what was submitted to the gate. Ben Carter owns it. `june`
says whether the June registry, which counted what engineers submitted
to the gate, would have counted the change as a release at all.
Lakeshore figures are illustrative.
"""
from __future__ import annotations

from collections import Counter
from dataclasses import dataclass

from .bundle import KINDS


@dataclass(frozen=True)
class Entry:
    rid: str
    date: str
    kind: str
    change: str
    june: bool                 # counted by the June registry's rule
    path: str                  # stages it passed, in order
    result: str                # full, rolled_back
    owner: str


LOG = (
    Entry("R-0713", "07-13", "policy", "pb-2026.07.13", False,
          "gate>shadow>full", "full", "Owen Fletcher"),
    Entry("R-0714", "07-14", "tool", "payments 3.1: split refunds",
          True, "gate>full", "full", "Daniel Price"),
    Entry("R-0716", "07-16", "prompt", "notice@7 wording", False,
          "gate>full", "full", "Dr. Hannah Clarke"),
    Entry("R-0721", "07-21", "memory", "traveler memory re-index",
          False, "gate>shadow>full", "full", "Dr. Hannah Clarke"),
    Entry("R-0722", "07-22", "harness", "settings: keep_turns 8 to 10",
          False, "gate>shadow>full", "full", "Daniel Price"),
    Entry("R-0723", "07-23", "harness", "harness 1.1.0: refund machine",
          True, "gate>shadow>canary", "rolled_back", "Daniel Price"),
    Entry("R-0727", "07-27", "policy", "pb-2026.07.27", False,
          "gate>shadow>canary>full", "full", "Owen Fletcher"),
    Entry("R-0729", "07-29", "tool", "offers 1.4: fare families", True,
          "gate>shadow>canary>full", "full", "Daniel Price"),
    Entry("R-0731", "07-31", "model", "change-intent student, July",
          True, "gate>shadow>canary>full", "full", "Dr. Hannah Clarke"),
    Entry("R-0803", "08-03", "memory", "fare-rules extract 2026-08",
          True, "gate>shadow>full", "full", "Dr. Hannah Clarke"),
    Entry("R-0804", "08-04", "prompt", "instruction file v11", True,
          "gate>shadow>canary>full", "full", "Daniel Price"),
    Entry("R-0805", "08-05", "tool", "registry: rebook description",
          False, "gate>shadow>canary>full", "full", "Daniel Price"),
    Entry("R-0806", "08-06", "model", "desk-note on dated mid model",
          False, "gate>shadow>canary>full", "full", "Dr. Hannah Clarke"),
    Entry("R-0810", "08-10", "policy", "pb-2026.08.10",
          False, "gate>shadow>canary>full", "full", "Owen Fletcher"),
    Entry("R-0811", "08-11", "prompt", "refund-reason@1.4", False,
          "gate>shadow>canary>full", "full", "Dr. Hannah Clarke"),
    Entry("R-0812", "08-12", "prompt", "change-intent@1.1: combined",
          False, "gate>shadow>canary>full", "full", "Dr. Hannah Clarke"),
    Entry("R-0813", "08-13", "harness", "harness 1.1.1: refund machine",
          True, "gate>shadow>canary>full", "full", "Daniel Price"),
    Entry("R-0817", "08-17", "tool", "rebook 2.2: renumbered flights",
          True, "gate>shadow>canary>full", "full", "Daniel Price"),
    Entry("R-0819", "08-19", "memory", "traveler memory schema 3",
          False, "gate>shadow>canary", "rolled_back", "Daniel Price"),
    Entry("R-0824", "08-24", "policy", "pb-2026.08.24", False,
          "gate>shadow>canary>full", "full", "Owen Fletcher"),
    Entry("R-0825", "08-25", "model", "frontier step on dated model",
          False, "gate>shadow>canary>full", "full", "Dr. Hannah Clarke"),
    Entry("R-0826", "08-26", "prompt", "notice@8 wording (A/B)", False,
          "gate>shadow>ab>full", "full", "Dr. Hannah Clarke"),
    Entry("R-0827", "08-27", "tool", "credits 1.3: expiry dates", True,
          "gate>shadow>canary>full", "full", "Daniel Price"),
)


def counts(log=LOG) -> dict:
    by = Counter(e.kind for e in log)
    return {
        "releases": len(log),
        "kinds": sum(1 for k in KINDS if by[k]),
        "by_kind": {k: by[k] for k in KINDS},
        "june_rule": sum(e.june for e in log),
        "rolled_back": [e.rid for e in log if e.result == "rolled_back"],
        "canaried": sum("canary" in e.path for e in log),
        "shadowed": sum("shadow" in e.path for e in log),
        "ab": sum(">ab>" in e.path for e in log),
        # a production regression is a release that reached full
        # exposure and was then found worse than the bundle it replaced
        "production_regressions": 0,
    }


def card(log=LOG) -> list[str]:
    c = counts(log)
    kinds = ", ".join(f"{k} {n}" for k, n in c["by_kind"].items())
    return [
        "change card, July 13 to August 31, 2026 (Ben Carter)",
        f"  releases               {c['releases']} of {c['kinds']} kinds",
        f"    {kinds}",
        f"  counted by June's rule {c['june_rule']}",
        f"  through shadow         {c['shadowed']}",
        f"  through canary         {c['canaried']}",
        f"  fixed-horizon A/B      {c['ab']}",
        f"  rolled back            {len(c['rolled_back'])}  "
        f"({', '.join(c['rolled_back'])}, both at canary)",
        f"  regressions in prod.   {c['production_regressions']}",
        "  unbundled changes      0 (trail check, daily)",
    ]
