"""Figure 37.1  Objectives for a system that acts.

Reading order: one row per objective, top to bottom; what it reads,
the target, the record it is read from, and who answers for it.
From reliability.objectives (Lakeshore figures are illustrative).
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "04-code" / "designlab"))
import figlib as fl  # noqa: E402
from matplotlib.patches import Rectangle  # noqa: E402

rows = (("Verified outcomes", "99.0%", "Reconciler", "Marcus Bell", "verified"),
        ("Unauthorized", "Zero", "Gateway", "Owen Fletcher", "ops"),
        ("Task latency", "95% in 40 s", "Traces", "Marcus Bell", "ops"),
        ("Cost per outcome", "90% of days", "Provider", "Daniel Price", "ops"),
        ("Backlog", "98% in 60 min", "Desk", "Marcus Bell", "ops"))
cols = (0.0, 1.35, 2.55, 3.55)
heads = ("Objective", "Target", "Read from", "Owner")
fig, ax = fl.figure(4.5, 3.0)
n = len(rows)
ax.set_xlim(0, 4.75)
ax.set_ylim(-0.1, n + 0.9)
ax.axis("off")
for x, h in zip(cols, heads):
    ax.text(x + 0.05, n + 0.45, h, va="center", fontsize=9.5,
            fontweight="bold", color=fl.INK)
for i, (*cells, tok) in enumerate(rows):
    y = n - 1 - i
    ax.add_patch(Rectangle((0.0, y + 0.06), 4.75, 0.88,
                           facecolor=fl.FILL[tok], edgecolor=fl.C[tok],
                           lw=1.5 if tok == "verified" else 0.75))
    for x, s in zip(cols, cells):
        ax.text(x + 0.05, y + 0.5, s, va="center", fontsize=9,
                color=fl.INK, fontweight="bold" if x == cols[0] else None)
fl.save(fig)
