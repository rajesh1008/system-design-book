"""Figure 43.10  Patterns that recur.

Reading order: one row per pattern, one column per design (telecom,
rebooking, refunds, bank, claims, collections). A filled square means
the pattern holds in that design. The top six hold in all six designs
and belong to the method; the bottom three vary by industry. From
designs.patterns.table on the six shipped designs.
"""
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[2] / "04-code" / "designlab"))
import figlib as fl  # noqa: E402
from matplotlib.patches import Rectangle  # noqa: E402

from designs import DESIGNS  # noqa: E402
from designs.patterns import table  # noqa: E402

names = ("Permission outside loop", "Independent verifier",
         "Status from chain", "Promised hand-off",
         "Rules outside prompt", "Tier by amount",
         "Person decides", "Never taken",
         "Signed surge rule")
heads = ("Tel", "Rbk", "Rfd", "Bnk", "Clm", "Col")
rows = table({d: DESIGNS[d] for d in list(DESIGNS)[:6]})
fig, ax = fl.figure(4.5, 3.4)
n = len(rows)
x0, cw = 2.55, 0.4
ax.set_xlim(0, x0 + cw * 6 + 0.05)
ax.set_ylim(-0.2, n + 0.9)
ax.axis("off")
for j, h in enumerate(heads):
    ax.text(x0 + cw * j + cw / 2, n + 0.35, h, ha="center", va="center",
            fontsize=9, fontweight="bold", color=fl.INK)
for i, ((_, row), label) in enumerate(zip(rows, names)):
    y = n - 1 - i
    every = all(row)
    ax.text(0.0, y + 0.5, label, va="center", fontsize=9, color=fl.INK,
            fontweight="bold" if every else None)
    for j, ok in enumerate(row):
        tok = "verified" if every else "ops"
        ax.add_patch(Rectangle((x0 + cw * j + 0.06, y + 0.12), cw - 0.12,
                               0.76, facecolor=fl.C[tok] if ok else "white",
                               edgecolor=fl.C[tok], lw=0.75,
                               hatch=None if every or not ok else "///"))
ax.plot([0, x0 + cw * 6], [3.0, 3.0], color=fl.GREY_DARK, lw=0.75,
        ls="--")
fl.save(fig)
