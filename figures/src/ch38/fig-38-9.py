"""Figure 38.9  The economics scorecard in operation.

Reading order: one row per measure, top to bottom; the August value,
what it is read against, and the owner. The cost per verified outcome
is highlighted. From economics.card (Lakeshore figures are
illustrative).
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "04-code" / "designlab"))
import figlib as fl  # noqa: E402
from matplotlib.patches import Rectangle  # noqa: E402
from economics import card  # noqa: E402

short = ("Cost per outcome", "Loops with a policy", "Storm, replayed")
notes = ("band $1.58-1.75", "2 of 2, gateway", "$11,406 as run")
rows = [(s, v, n, o) for s, n, (_m, v, _n, o)
        in zip(short, notes, card.cells())]
cols = (0.0, 1.85, 2.55, 3.95)
heads = ("Measure", "Aug.", "Read against", "Owner")
fig, ax = fl.figure(4.5, 3.0)
n = len(rows)
ax.set_xlim(0, 5.15)
ax.set_ylim(-0.1, n + 0.9)
ax.axis("off")
for x, h in zip(cols, heads):
    ax.text(x + 0.05, n + 0.45, h, va="center", fontsize=9.5,
            fontweight="bold", color=fl.INK)
for i, cells in enumerate(rows):
    y = n - 1 - i
    tok = "verified" if i == 0 else "ops"
    ax.add_patch(Rectangle((0.0, y + 0.06), 5.15, 0.88,
                           facecolor=fl.FILL[tok], edgecolor=fl.C[tok],
                           lw=1.5 if tok == "verified" else 0.75))
    for x, s in zip(cols, cells):
        ax.text(x + 0.05, y + 0.5, s, va="center", fontsize=9,
                color=fl.INK, fontweight="bold" if x == cols[0] else None)
fl.save(fig)
