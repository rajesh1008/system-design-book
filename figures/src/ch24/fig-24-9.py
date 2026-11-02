"""Figure 24.9  The knowledge operations scorecard.

Reading order: one row per line, top to bottom: retrieval, freshness,
memory, outcomes. Values for the week of June 1, 2026, reviewed
Monday, June 8, with the owner of each line. The alert lines are in
knowops.card and Section 6 (Lakeshore figures are illustrative).
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "04-code" / "designlab"))
import figlib as fl  # noqa: E402
from knowops.card import ROWS  # noqa: E402
from matplotlib.patches import Rectangle  # noqa: E402

short = ("Golden set", "Fresh sample", "Notices on time",
         "Stale bookings", "Past TTL", "Superseded",
         "Unlabeled pins", "Wrong city", "Verifier splits")
tok = {"retrieval": "knowledge", "freshness": "policy",
       "memory": "knowledge", "outcomes": "verified"}
cols = (0.0, 1.85, 3.05)
heads = ("Line", "Value", "Owner")
fig, ax = fl.figure(4.5, 4.4)
n = len(ROWS)
ax.set_xlim(0, 4.6)
ax.set_ylim(-0.1, n + 0.9)
ax.axis("off")
for x, h in zip(cols, heads):
    ax.text(x + 0.05, n + 0.45, h, va="center", fontsize=10,
            fontweight="bold", color=fl.INK)
for i, (row, name) in enumerate(zip(ROWS, short)):
    area, _m, val, _a, own = row
    y = n - 1 - i
    t = tok[area]
    ax.add_patch(Rectangle((0.0, y + 0.06), 4.6, 0.88,
                           facecolor=fl.FILL[t], edgecolor=fl.C[t], lw=0.75))
    own = own.replace("Dr. ", "").split()[-1]
    for x, txt in zip(cols, (name, val, own)):
        ax.text(x + 0.05, y + 0.5, txt, va="center", fontsize=9.5,
                color=fl.INK, fontweight="bold" if x == cols[1] else None)
fl.save(fig)
