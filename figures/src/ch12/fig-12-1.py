"""Figure 12.1  The failure catalog by plane.

Reading order: one band per plane, top to bottom (action, control,
knowledge, trail, and the path outside the planes); each row names a
failure mode, its kind, and what sees it. From failure.catalog.
"""
import sys
from pathlib import Path

import figlib as fl
from matplotlib.patches import Rectangle

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "04-code" / "designlab"))
from failure.catalog import CATALOG  # noqa: E402

TOK = {"action": "ops", "control": "policy", "knowledge": "knowledge",
       "trail": "evidence", "outside": "fail"}
n = len(CATALOG)
fig, ax = fl.figure(4.5, 6.75)
ax.axis("off")
ax.set_xlim(0, 10)
ax.set_ylim(-0.1, n + 1.1)
for x, h in ((0.1, "Plane"), (1.75, "Failure mode; kind, seen by")):
    ax.text(x, n + 0.5, h, ha="left", va="center", fontsize=9.5,
            fontweight="bold")
start = 0
for i, f in enumerate(CATALOG):
    y = n - 1 - i
    tok = TOK[f.plane]
    ax.add_patch(Rectangle((1.6, y + 0.06), 8.35, 0.88,
                           facecolor=fl.FILL[tok],
                           edgecolor=fl.C[tok] if f.plane == "outside"
                           else "none", lw=fl.STROKE["emphasis"]))
    ax.text(1.75, y + 0.68, f.mode, va="center", fontsize=9.5)
    ax.text(1.75, y + 0.29, f"{f.kind}, seen by {f.seen_by}",
            va="center", fontsize=9, color=fl.LABEL[tok])
    last = i == n - 1 or CATALOG[i + 1].plane != f.plane
    if last:
        top = n - start
        ax.add_patch(Rectangle((0.05, y + 0.06), 1.5, top - y - 0.12,
                               facecolor="white", edgecolor=fl.C[tok],
                               lw=fl.STROKE["data"]))
        ax.text(0.8, (y + top) / 2,
                "know-\nledge" if f.plane == "knowledge" else f.plane, ha="center", va="center",
                fontsize=9, color=fl.LABEL[tok], fontweight="bold")
        start = i + 1
fl.save(fig)
