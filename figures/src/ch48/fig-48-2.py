"""Figure 48.2  The renaming cycle.

Reading order: top to bottom, oldest name first, one row per name
under which this kind of product reached Lakeshore, from the 2024
chatbot pilot to an October 2026 pitch. The four squares are the four
questions that stay: effect, permission, verification, and trail; a
filled square is answered, an empty one is a gap. Only the bold row,
Lakeshore's own chain, fills all four. From plan.core.renames.
"""
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[2] / "04-code" / "designlab"))
import figlib as fl  # noqa: E402
from matplotlib.patches import Rectangle  # noqa: E402

from plan.core import LINKS, renames  # noqa: E402

rs = sorted(renames(), key=lambda r: r.date)
fig, ax = fl.figure(4.5, 3.4)
n = len(rs)
x0, cw = 2.45, 0.52
ax.set_xlim(0, x0 + cw * 4 + 0.05)
ax.set_ylim(-0.2, n + 0.9)
ax.axis("off")
for j, h in enumerate(("Effect", "Perm.", "Verif.", "Trail")):
    ax.text(x0 + cw * j + cw / 2, n + 0.35, h, ha="center", va="center",
            fontsize=9, fontweight="bold", color=fl.INK)
for i, r in enumerate(rs):
    y = n - 1 - i
    ours = not r.missing
    tok = "verified" if ours else "org"
    ax.text(0.0, y + 0.5, f"{r.date[:7]}  {r.name}", va="center",
            fontsize=9, color=fl.INK, fontweight="bold" if ours else None)
    for j, k in enumerate(LINKS):
        ok = k not in r.missing
        ax.add_patch(Rectangle((x0 + cw * j + 0.07, y + 0.14), cw - 0.14,
                               0.72, facecolor=fl.C[tok] if ok else "white",
                               edgecolor=fl.C[tok], lw=0.75 if not ours
                               else 1.5))
fl.save(fig)
