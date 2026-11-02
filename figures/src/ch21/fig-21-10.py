"""Figure 21.10  The context scorecard.

Reading order: one row per measure, top to bottom, from the context card
in the lab replay as of May 31, 2026 (rows shortened; the lab prints
eleven). The highlighted row is the one the
chapter set out to move: success on runs of 17 to 24 steps, 98.3%
against 90.7% before. Every row passes.
"""
import figlib as fl
from matplotlib.patches import Rectangle

rows = [("Budget a step", "48,000"),
        ("Compact at", "33,600"),
        ("Peak, p95", "31,015"),
        ("Over budget", "0"),
        ("Lost facts", "0"),
        ("1-4 steps", "98.1%"),
        ("17-24 steps", "98.3% (was 90.7%)"),
        ("Instructions", "v9, 0 findings")]
HI = 6

fig, ax = fl.figure(4.5, 3.4)
n = len(rows)
ax.set_xlim(0, 10)
ax.set_ylim(-0.1, n + 0.9)
ax.axis("off")
for x, h in ((0.15, "Measure"), (4.4, "Value"), (9.0, "Check")):
    ax.text(x, n + 0.4, h, fontsize=10, fontweight="bold", va="center")
for i, (m, v) in enumerate(rows):
    y = n - 1 - i
    if i == HI:
        ax.add_patch(Rectangle((0, y + 0.04), 10, 0.92,
                               facecolor=fl.FILL["verified"],
                               edgecolor=fl.C["verified"], lw=1.6))
    else:
        ax.add_patch(Rectangle((0, y + 0.04), 10, 0.92, facecolor="white",
                               edgecolor=fl.C["model"], lw=0.5))
    w = "bold" if i == HI else "normal"
    ax.text(0.15, y + 0.5, m, fontsize=10, va="center", fontweight=w)
    ax.text(4.4, y + 0.5, v, fontsize=10, va="center", fontweight=w)
    ax.text(9.0, y + 0.5, "ok", fontsize=10, va="center",
            color=fl.LABEL["verified"], fontweight="bold")
fl.save(fig)
