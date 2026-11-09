"""Figure 44.1  The pilot and its numbers.

Reading order: one row per milestone from the pilot's first day to
the year-end card, top to bottom: the date, what changed, and the
number the scoreboard carried. The last row, in green, is the
year-end card filed September 30, 2026. From golive.pilot
(Lakeshore figures are illustrative).
"""
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[2] / "04-code" / "designlab"))
sys.path.insert(0, str(HERE))
import figlib as fl  # noqa: E402
from _table import table  # noqa: E402

from golive.pilot import CARD  # noqa: E402

a, s, v, c, p, i = CARD["Dec 2025"]
y = CARD["Sep 2026"]
rows = (("Nov 2025", "Pilot, 2%", "Refunds to $1,500"),
        ("Dec 2025", f"Agent {a:.1%}", f"{v:.1%}, ${c:.2f}"),
        ("Mar 2026", "Phase two", "Agent 4%"),
        ("Jun 2026", "General release", "Agent 14%"),
        ("Sep 2026", f"Agent {y[0]:.0%}", f"{y[2]:.1%}, ${y[3]:.2f}"))
toks = ["ops"] * 4 + ["verified"]
fig, ax = table(rows, ("Month", "Stage", "Card"),
                (0.0, 1.25, 2.95), width=5.0, toks=toks, h=3.0, fs=9)
fl.save(fig)
