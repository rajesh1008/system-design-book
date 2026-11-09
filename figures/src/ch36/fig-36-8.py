"""Figure 36.8  The assurance scorecard.

Reading order: one row per line, top to bottom; the value for June
2026 and the person who owns the line (surname; the alt text and the
text give full names). Each value is computed from
the trail, the anchors, the battery, or the findings register, not
typed. From assurance.scorecard (Lakeshore figures are illustrative).
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "04-code" / "designlab"))
import figlib as fl  # noqa: E402
from matplotlib.patches import Rectangle  # noqa: E402

rows = (("Open findings", "1 (closed, 9 days)", "Vasquez", "evidence"),
        ("Refunds in pack", "5,967", "Carter", "evidence"),
        ("Complete chains", "60 of 60", "Vasquez", "verified"),
        ("Unregistered\ndestinations", "1 proposed, 0 paid", "Fletcher", "verified"),
        ("Days anchored", "30 of 30", "Morgan", "verified"),
        ("Battery effects", "0 of 62", "Fletcher", "verified"))
cols = (0.0, 1.75, 3.25)
heads = ("Line", "June", "Owner")
fig, ax = fl.figure(4.6, 3.4)
n = len(rows)
ax.set_xlim(0, 4.6)
ax.set_ylim(-0.1, n + 0.9)
ax.axis("off")
for x, h in zip(cols, heads):
    ax.text(x + 0.05, n + 0.45, h, va="center", fontsize=10,
            fontweight="bold", color=fl.INK)
for i, (*cells, tok) in enumerate(rows):
    y = n - 1 - i
    ax.add_patch(Rectangle((0.0, y + 0.06), 4.6, 0.88, facecolor="white",
                           edgecolor=fl.GREY_LIGHT, lw=0.75))
    ax.add_patch(Rectangle((cols[1], y + 0.06), cols[2] - cols[1] - 0.05,
                           0.88, facecolor=fl.FILL[tok],
                           edgecolor=fl.C[tok], lw=0.75))
    for x, t in zip(cols, cells):
        ax.text(x + 0.05, y + 0.5, t, va="center", fontsize=9,
                color=fl.INK, fontweight="bold" if x == cols[0] else None)
fl.save(fig)
