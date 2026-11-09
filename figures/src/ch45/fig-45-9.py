"""Figure 45.10  Patterns that recur across twelve designs.

Reading order: one row per pattern, one column per design, Chapter
43's six customer-facing designs on the left and Chapter 45's six
internal designs on the right of the vertical rule. A filled teal
square means the pattern holds. The top five rows hold in all twelve;
the bottom three are new patterns that only the internal designs were
asked to show (amber). From designs.patterns and designs.internal.
"""
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[2] / "04-code" / "designlab"))
import figlib as fl  # noqa: E402
from matplotlib.patches import Rectangle  # noqa: E402

from designs import internal  # noqa: E402
from designs.patterns import PATTERNS  # noqa: E402

names = ("Permission outside loop", "Independent verifier",
         "Status from chain", "Promised hand-off",
         "Rules outside", "Tier by amount",
         "Person decides", "Never taken", "Surge rule",
         "No standing access", "Loop, 7 properties",
         "Other signer")
heads = ("Tel", "Rbk", "Rfd", "Bnk", "Clm", "Col",
         "Res", "Cod", "Ana", "Ops", "Cmp", "Rec")
with internal.installed() as designs:
    specs = list(designs.values())
    pats = list(PATTERNS) + list(internal.PATTERNS)
    rows = [[fn(s) for s in specs] for _, fn in pats]
fig, ax = fl.figure(4.5, 3.6)
n = len(rows)
x0, cw = 1.95, 0.215
ax.set_xlim(0, x0 + cw * 12 + 0.05)
ax.set_ylim(-0.2, n + 1.0)
ax.axis("off")
for j, h in enumerate(heads):
    ax.text(x0 + cw * j + cw / 2, n + 0.45, h, ha="center", va="center",
            fontsize=9, rotation=90, color=fl.INK)
for i, (row, label) in enumerate(zip(rows, names)):
    y = n - 1 - i
    every = all(row)
    new = i >= len(PATTERNS)
    tok = "policy" if new else "ops"
    ax.text(0.0, y + 0.5, label, va="center", fontsize=9, color=fl.INK,
            fontweight="bold" if every else None)
    for j, ok in enumerate(row):
        ax.add_patch(Rectangle((x0 + cw * j + 0.03, y + 0.12),
                               cw - 0.06, 0.76,
                               facecolor=fl.FILL[tok] if ok else "white",
                               edgecolor=fl.C[tok], lw=0.75))
ax.vlines(x0 + cw * 6, 0, n, colors=fl.GREY_DARK, lw=0.75,
          linestyles="--")
fl.save(fig)
