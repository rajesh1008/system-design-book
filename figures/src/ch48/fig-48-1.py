"""Figure 48.1  The final scoreboard.

Reading order: one row per number on Lakeshore's scoreboard, top to
bottom, in three columns: the October 14, 2025 baseline, the target
its owner set, and the year-end card of September 30, 2026 that the
board read on October 22. The green rows are the four numbers the
book opened on: cost, verification, permission, and the trail. From
plan.core.card on plan/data/card.toml. Lakeshore figures are
illustrative.
"""
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parents[2] / "04-code" / "designlab"))
import figlib as fl  # noqa: E402,F401
from _table import table  # noqa: E402

from plan.core import card  # noqa: E402

SHORT = {"cost_blended": "Cost per change", "cost_agent": "Per verified",
         "people_share": "Person handles", "verified": "Verified",
         "unauthorized": "Unauthorized", "refund_error": "Refund error",
         "duplicates": "Duplicates", "incidents": "Incidents",
         "p95": "Task p95", "annual": "Annual cost"}
KEY4 = {"cost_blended", "verified", "unauthorized", "refund_error"}
c = card()
rows, toks = [], []
for r in c["row"]:
    rows.append((SHORT[r["key"]], r["baseline"], r["target"],
                 r["year_end"]))
    toks.append("verified" if r["key"] in KEY4 else "ops")
fig, ax = table(rows, ("Number", "Baseline", "Target", "Year end"),
                (0.0, 1.75, 2.85, 4.15), width=5.0, toks=toks, h=3.4)
fl.save(fig)
