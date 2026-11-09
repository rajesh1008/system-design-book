"""Figure 7.5  Supplier idempotency support by type.

Reading order: one row per supplier type, top to bottom; columns are
the three contracts. Generated from 04-code/designlab/corpus/tools.py.
Each cell is the number of the eighteen lab tools with that contract.
"""
import sys
from pathlib import Path

import figlib as fl
from matplotlib.patches import Rectangle

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "04-code" / "designlab"))
from corpus.tools import counts  # noqa: E402

names = {"airline": "Airline", "hotel": "Hotel", "car": "Car rental",
         "payment": "Payment processor", "ledger": "Voucher ledger",
         "message": "Customer message"}
cols = (("native", "Native key", "verified"),
        ("lookup", "Lookup", "knowledge"),
        ("none", "None", "fail"))
c = counts()
rows = [k for k in names if k in c]
fig, ax = fl.figure(4.5, 3.0)
ax.set_xlim(0, 10)
ax.set_ylim(0, len(rows) + 1)
ax.axis("off")
x0, w = 4.2, 1.9
for j, (_, title, _) in enumerate(cols):
    ax.text(x0 + j * w + w / 2, len(rows) + 0.5, title, ha="center",
            va="center", fontweight="bold")
for i, k in enumerate(rows):
    y = len(rows) - i - 0.5
    ax.text(0.1, y, names[k], va="center")
    for j, (key, _, tok) in enumerate(cols):
        n = c[k][key]
        if n:
            ax.add_patch(Rectangle((x0 + j * w + 0.15, y - 0.36), w - 0.3,
                                   0.72, facecolor=fl.FILL[tok],
                                   edgecolor=fl.C[tok],
                                   lw=fl.STROKE["data"],
                                   hatch="///" if key == "none" else ""))
        ax.text(x0 + j * w + w / 2, y, str(n) if n else "", ha="center",
                va="center", fontweight="bold", color=fl.LABEL[tok],
                bbox=dict(facecolor="white", edgecolor="none", pad=1.2)
                if n else None)
    ax.plot([0, 10], [y - 0.5, y - 0.5], color=fl.GREY_LIGHT, lw=0.5,
            linestyle="-", marker="")
fl.save(fig)
