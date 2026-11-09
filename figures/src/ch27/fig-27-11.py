"""Figure 27.11  The topology decision table.

Reading order: one row per situation, top to bottom: the situation, the
topology Lakeshore uses, and the evidence behind it. From DR-27.1 and
the chapter's lab. Lakeshore figures are illustrative.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
import figlib as fl  # noqa: E402
from matplotlib.patches import Rectangle  # noqa: E402

rows = (("1 or 2 legs", "One agent", "96.3% vs 92.8%", "verified"),
        ("3+ legs", "Lead, workers", "88.0% vs 64.2%", "evidence"),
        ("Desk research", "Read-only\nworkers", "cited, checked", "knowledge"),
        ("Eligibility", "Agent and\nverifier", "95.7% at 1.11x", "policy"),
        ("Deeper levels", "Not used", "facts lost", "fail"))
cols = (0.0, 1.45, 2.95)
heads = ("Situation", "Topology", "Evidence")
fig, ax = fl.figure(4.5, 3.4)
n = len(rows)
ax.set_xlim(0, 4.6)
ax.set_ylim(-0.1, n + 0.8)
ax.axis("off")
for x, h in zip(cols, heads):
    ax.text(x + 0.05, n + 0.4, h, va="center", fontsize=10,
            fontweight="bold", color=fl.INK)
for i, (sit, top, ev, tok) in enumerate(rows):
    yy = n - 1 - i
    ax.add_patch(Rectangle((0.0, yy + 0.05), 4.6, 0.9,
                           facecolor=fl.FILL[tok], edgecolor=fl.C[tok],
                           lw=0.75))
    for x, t, size in zip(cols, (sit, top, ev), (10, 10, 10)):
        ax.text(x + 0.05, yy + 0.5, t, va="center", fontsize=size,
                color=fl.INK, fontweight="bold" if x == cols[1] else None)
fl.save(fig)
