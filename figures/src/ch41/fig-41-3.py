"""Figure 41.3  Roles and their planes.

Reading order: one row per role, top to bottom: the six roles on the
team with their seats as of August 31, 2026 (eleven with two signed
hires), and the plane each works in; then the two
partners, who hold decisions but are not headcount. From org.roles
(Lakeshore figures are illustrative).
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "04-code" / "designlab"))
import figlib as fl  # noqa: E402
from matplotlib.patches import Rectangle  # noqa: E402

rows = (("Lead", "1", "All four", "org"),
        ("Systems architect", "1", "All four", "org"),
        ("Agent engineer", "3", "Action, knowledge", "org"),
        ("Platform engineer", "2", "Control", "org"),
        ("Evaluation engineer", "2", "Trail", "org"),
        ("SRE", "2", "All four", "ops"),
        ("Security partner", "-", "Control", "policy"),
        ("Risk partner", "-", "Control", "policy"))
heads = ("Role", "Seats", "Plane")
cols = (0.0, 2.2, 3.0)
fig, ax = fl.figure(4.5, 3.4)
n = len(rows)
W = 4.9
ax.set_xlim(0, W)
ax.set_ylim(-0.1, n + 0.9)
ax.axis("off")
for x, h in zip(cols, heads):
    ax.text(x + 0.05, n + 0.45, h, va="center", fontsize=9.5,
            fontweight="bold", color=fl.INK)
for i, (*cells, tok) in enumerate(rows):
    y = n - 1 - i
    ax.add_patch(Rectangle((0.0, y + 0.06), W, 0.88,
                           facecolor=fl.FILL[tok], edgecolor=fl.C[tok],
                           lw=0.75, ls="--" if tok == "policy" else "-"))
    for x, s in zip(cols, cells):
        ax.text(x + 0.05, y + 0.5, s, va="center", fontsize=9,
                color=fl.INK, fontweight="bold" if x == cols[0] else None)
fl.save(fig)
