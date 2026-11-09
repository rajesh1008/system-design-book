"""The pilot and its numbers: November 3, 2025, to the general-
availability ramp on June 1, 2026. Figures are the ones the monthly
scoreboard and the pilot traces carry (Lakeshore figures are
illustrative)."""
from __future__ import annotations

PILOT = {
    "started": "Mon Nov 3, 2025",
    "share": "about 2% of changes",
    "refund_limit_usd": 1_500,
    "chain_record_live": "Mon Dec 15, 2025",
    "phase_two": "Mon Mar 2, 2026",
    "ga": "Mon Jun 1, 2026",
}
TRACES = {"sessions": 21_367, "tasks": 10_527, "rebook": 4_459,
          "refund": 3_393, "cancel": 1_601, "credit": 1_074}

# month: agent, assisted, verified, cost per VO, p95 s, incidents
CARD = {
    "Dec 2025": (0.009, 0.02, 0.979, 4.10, 52, 0),
    "Mar 2026": (0.04, 0.08, 0.988, 2.60, 47, 1),
    "Apr 2026": (0.025, 0.09, 0.981, 2.95, 45, 2),
    "May 2026": (0.06, 0.12, 0.991, 1.84, 41, 3),
    "Jun 2026": (0.14, 0.16, 0.993, 1.79, 40, 4),
    "Aug 2026": (0.36, 0.23, 0.996, 1.61, 37, 6),
    "Sep 2026": (0.44, 0.24, 0.995, 1.61, 38, 7),
}


def lines() -> list[str]:
    out = [f"pilot from {PILOT['started']}, {PILOT['share']},",
           f"refunds to ${PILOT['refund_limit_usd']:,}; chain record "
           f"live {PILOT['chain_record_live']}",
           f"traces: {TRACES['sessions']:,} sessions, "
           f"{TRACES['tasks']:,} tasks (rebook {TRACES['rebook']:,}, "
           f"refund {TRACES['refund']:,},",
           f"  cancel {TRACES['cancel']:,}, credit {TRACES['credit']:,})",
           "",
           f"{'month':<9}{'agent':>7}{'assist':>8}{'verified':>10}"
           f"{'$/VO':>7}{'p95':>6}{'inc':>5}"]
    for m, (a, s, v, c, p, i) in CARD.items():
        out.append(f"{m:<9}{a * 100:>6.1f}%{s * 100:>7.0f}%"
                   f"{v * 100:>9.1f}%{c:>7.2f}{p:>5}s{i:>5}")
    return out
