"""The charter text and the team card (Chapter 41's closing card).

Lakeshore figures are illustrative.
"""
from __future__ import annotations

from datetime import date

from .rights import MATRICES, SIGNERS, check_all, owners
from .rhythm import FORUMS, unreviewed, weekly_hours
from .roles import AS_OF, PARTNERS, SEATS, seated
from .skills import gaps

CHARTER = (
    "Agent platform team charter, v1, Monday, August 17, 2026",
    "",
    "The team's new product is not the agent; it is the evidence",
    "that the agent may act.",
    "",
    "We own: the harness and tools (action), the gateway, identity",
    "  broker and budgets (control), the corpora and their freshness",
    "  (knowledge), the trail, the gates and the cards (trail).",
    "We do not own: what a rule says, what a risk tier is, which",
    "  scopes a tool gets, or what customers are told. Partners own",
    "  those; we build the place where their decisions take effect.",
    "Every decision has one owner and a deputy. A decision with two",
    "  owners has none. The author of a change never approves it.",
    "We measure ourselves by the scoreboard, not by agents shipped.",
    "We test this charter against six scenarios before an incident",
    "  tests it, and again whenever a seat or a partner changes.",
)


def card(day: date = AS_OF) -> dict:
    m = MATRICES["2026-08-21"]
    results = check_all(m, SIGNERS["2026-08-21"])
    passed = sum(1 for _, f in results if not f)
    later = date(2026, 9, 14)
    return {
        "filed": "Monday, August 31, 2026",
        "team size": f"{len(SEATS)} ({len(seated(day))} seated, "
                     f"{len(SEATS) - len(seated(day))} signed)",
        "roles": len({s.title for s in SEATS}),
        "partners": f"{len(PARTNERS)} people in "
                    f"{len({p.team for p in PARTNERS})} functions",
        "redefined role": "agent systems architect",
        "  was": "ML engineer, agents (June requisition)",
        "decisions": f"{len(m)}, one owner each, "
                     f"{len(owners(m))} owners",
        "scenarios": f"{passed} of {len(results)} pass",
        "skill gaps Aug 31": ", ".join(gaps(day)) or "none",
        "skill gaps Sep 14": ", ".join(gaps(later)) or "none",
        "forums": f"{len(FORUMS)}, {weekly_hours():.1f} hours a week, "
                  f"{len(unreviewed())} unreviewed",
        "owner": "Daniel Price",
        "reviewed": "Rachel Morgan",
    }
