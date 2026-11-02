"""Figure 9.10  The durability scorecard.

Reading order: top to bottom, one row per measure, with its value, its
target, and where the number comes from. From durable.card.CARD.
"""
import sys
from pathlib import Path

import figlib as fl
from matplotlib.patches import Rectangle

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "04-code" / "designlab"))
from durable.card import CARD  # noqa: E402

fig, ax = fl.figure(4.5, 3.4)
ax.axis("off")
n = len(CARD)
ax.set_xlim(0, 10)
ax.set_ylim(0, n + 1)
heads = [(0.1, "Measure"), (5.6, "Value"), (6.9, "Target")]
for x, h in heads:
    ax.text(x, n + 0.5, h, fontweight="bold", fontsize=9, va="center")
for i, (m, v, t, src) in enumerate(CARD):
    y = n - 1 - i
    ax.add_patch(Rectangle((0, y + 0.06), 10, 0.88, facecolor=fl.FILL["ops"] if i % 2 == 0 else "white",
                           edgecolor=fl.C["ops"], lw=fl.STROKE["data"]))
    ax.text(0.1, y + 0.62, m, fontsize=9.5, va="center")
    ax.text(0.1, y + 0.28, src, fontsize=9, va="center", color=fl.LABEL["ops"])
    ax.add_patch(Rectangle((5.5, y + 0.2), 1.25, 0.6, facecolor=fl.FILL["verified"],
                           edgecolor=fl.C["verified"], lw=fl.STROKE["data"]))
    ax.text(6.12, y + 0.5, v, fontsize=9, va="center", ha="center", fontweight="bold")
    ax.text(6.9, y + 0.5, t, fontsize=9.5, va="center")
fl.save(fig)
