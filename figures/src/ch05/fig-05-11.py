"""Figure 5.11  The linter's three failures on v0.

Reading order: one row per failure, top to bottom (M1, M2, M3); the
finding from linting v0 on the left, the fix in v0.1 on the right.
Findings are produced by method.lint on the two design files.
"""
import sys
from pathlib import Path

import figlib as fl
from matplotlib.patches import FancyArrowPatch, Rectangle

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "04-code" / "designlab"))
from method.design import load  # noqa: E402
from method.lint import lint  # noqa: E402

v0 = lint(load("v0"))
assert len(v0) == 3 and not lint(load("v0_1"))
ITEM = {"EST-1": "M1", "OWN-1": "M2", "DEC-1": "M3"}
FIX = {"EST-1": "18.6 computed\nfrom seven sourced inputs",
       "OWN-1": "owner:\nMarcus Bell",
       "DEC-1": "three options;\nframework loop, pilot only"}
SHORT = {"EST-1": "peak 2,000 a second:\nno assumption or source",
         "OWN-1": "approval-queue\ndive: no owner",
         "DEC-1": "durable execution:\none option"}
fig, ax = fl.figure(4.5, 3.6)
ax.set_xlim(0, 10.5)
ax.set_ylim(0, 3.9)
ax.axis("off")
ax.text(2.6, 3.6, "v0, November 13", ha="center", fontweight="bold", color=fl.LABEL["fail"])
ax.text(8.05, 3.6, "v0.1, November 14", ha="center", fontweight="bold", color=fl.LABEL["verified"])
for i, f in enumerate(sorted(v0, key=lambda f: ITEM[f.rule])):
    y = 2.9 - i * 1.1
    ax.text(0.0, y, ITEM[f.rule], va="center", fontweight="bold")
    ax.add_patch(Rectangle((0.7, y - 0.45), 4.1, 0.9, facecolor=fl.FILL["fail"],
                           edgecolor=fl.C["fail"], lw=fl.STROKE["data"], linestyle="--"))
    ax.text(0.85, y + 0.22, f.rule, va="center", **fl.mono(f.rule))
    ax.text(0.85, y - 0.12, SHORT[f.rule], va="center", fontsize=9.5)
    ax.add_patch(Rectangle((5.6, y - 0.45), 4.9, 0.9, facecolor=fl.FILL["verified"],
                           edgecolor=fl.C["verified"], lw=fl.STROKE["control"]))
    ax.text(8.05, y, FIX[f.rule], ha="center", va="center", fontsize=9.5)
    ax.add_patch(FancyArrowPatch((4.85, y), (5.55, y), arrowstyle="-|>", mutation_scale=9,
                                 color=fl.INK, lw=fl.STROKE["control"]))
fl.save(fig)
