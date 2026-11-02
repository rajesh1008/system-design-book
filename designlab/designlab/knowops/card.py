"""The knowledge operations scorecard (fig-24-9).

One row per question the knowledge plane must answer every week, each
with its measure, its alert line, and the person who answers for it.
Values are the first weekly review, Monday, June 8, 2026, for the week
of June 1 (DR-24.1 live from June 2). Lakeshore figures are
illustrative.
"""
from __future__ import annotations

ROWS = (
    # (area, measure, value, alert when, owner)
    ("retrieval", "golden set, recall at ten", "89%", "below 85%",
     "Dr. Hannah Clarke"),
    ("retrieval", "fresh sample of 200, recall at ten", "88%",
     "gap +2 pts, clustered", "Dr. Hannah Clarke"),
    ("freshness", "notice changes indexed in 15 min (event)",
     "23 of 23", "any miss", "Dr. Hannah Clarke"),
    ("freshness", "booking reads older than 15 min at effect", "0",
     "any", "Ben Carter"),
    ("memory", "memories read past their TTL", "0", "any",
     "Daniel Price"),
    ("memory", "memories superseded by a record at read", "1,288",
     "trend only", "Daniel Price"),
    ("memory", "pins without a source label", "0", "any",
     "Daniel Price"),
    ("outcomes", "wrong-destination rebookings", "0", "any",
     "Marcus Bell"),
    ("outcomes", "verifier disagreements (pnr vs destination)", "0",
     "any", "Ben Carter"),
)


def lines() -> list[str]:
    out = []
    for area, measure, value, alert, owner in ROWS:
        out.append(f"{area:<10}{measure:<44}{value:>9}")
        out.append(f"{'':<10}alert: {alert}; owner: {owner}")
    return out
