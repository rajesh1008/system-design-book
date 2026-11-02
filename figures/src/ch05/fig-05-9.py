"""Figure 5.9  The review checklist by gap.

Reading order: top to bottom, five gap items then seven method items;
each row names the linter rules that decide it. From method.artifacts.
"""
import sys
from pathlib import Path

import figlib as fl
from matplotlib.patches import Rectangle

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "04-code" / "designlab"))
from method.artifacts import CHECKLIST  # noqa: E402

fig, ax = fl.figure(4.5, 4.6)
n = len(CHECKLIST)
ax.set_xlim(0, 10)
ax.set_ylim(0, n + 1.6)
ax.axis("off")
ax.text(0.1, n + 1.1, "Gap items", fontweight="bold", color=fl.LABEL["policy"], va="center")
y = n + 0.5
for k, (item, area, q, rules) in enumerate(CHECKLIST):
    if k == 5:
        y -= 0.15
        ax.text(0.1, y, "Method items", fontweight="bold", color=fl.LABEL["evidence"], va="center")
        y -= 0.85
    tok = "policy" if item.startswith("G") else "evidence"
    ax.add_patch(Rectangle((0, y - 0.42), 10, 0.84, facecolor=fl.FILL[tok] if item.startswith("G") else "white",
                           edgecolor=fl.C[tok], lw=fl.STROKE["data"]))
    ax.text(0.15, y, item, va="center", **fl.mono(item))
    ax.text(1.0, y, area, va="center", fontsize=9.5)
    ax.text(9.85, y, " ".join(rules), va="center", ha="right", **fl.mono("r"))
    y -= 1
fl.save(fig)
