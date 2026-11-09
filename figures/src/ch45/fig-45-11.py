"""Figure 45.11  Twelve designs, sixty gaps.

Reading order: one row per design, Chapter 43's six above the rule
and Chapter 45's six below it; one column per gap, G1 to G5. A green
square is a gap closed with an answer, an owner, and no finding. All
sixty are closed in the clean run. From designs.lint.gap_status with
designs.internal installed.
"""
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[2] / "04-code" / "designlab"))
import figlib as fl  # noqa: E402
from importlib import import_module  # noqa: E402
from matplotlib.patches import Rectangle  # noqa: E402

from designs import internal  # noqa: E402

worked = import_module("designs.lint")
with internal.installed() as designs:
    rows = [(d, worked.gap_status(s)) for d, s in designs.items()]
fig, ax = fl.figure(4.5, 3.4)
n = len(rows)
x0, cw = 2.1, 0.42
ax.set_xlim(0, x0 + cw * 5 + 0.1)
ax.set_ylim(-0.6, n + 0.9)
ax.axis("off")
for j in range(5):
    ax.text(x0 + cw * j + cw / 2, n + 0.4, f"G{j + 1}", ha="center",
            va="center", fontsize=9.5, fontweight="bold", color=fl.INK)
closed = 0
for i, (did, gs) in enumerate(rows):
    y = n - 1 - i
    ax.text(0.0, y + 0.5, did, va="center", fontsize=9, color=fl.INK)
    for j, g in enumerate(sorted(gs)):
        ok = gs[g]
        closed += ok
        ax.add_patch(Rectangle((x0 + cw * j + 0.05, y + 0.1), cw - 0.1,
                               0.8, lw=0.75, edgecolor=fl.C["verified"],
                               facecolor=fl.FILL["verified"] if ok
                               else "white"))
ax.hlines(6.0, 0, x0 + cw * 5, colors=fl.GREY_DARK, lw=0.75,
          linestyles="--")
ax.text(x0 + cw * 2.5, -0.35, f"{closed} of {5 * n} closed",
        ha="center", va="center", fontsize=9.5, fontweight="bold",
        color=fl.LABEL["verified"])
fl.save(fig)
