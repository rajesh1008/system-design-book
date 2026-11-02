"""Figure 15.9  Lab results: three routing rules.

Reading order: one bar per rule, top to bottom; bar length is cost per
task in the DesignLab bake-off, and the label gives tasks passed and
high-risk steps sent to a small model. The frontier rule is priced from
the same calls and not run (Lakeshore figures are illustrative).
"""
import sys
from pathlib import Path

from matplotlib.patches import Rectangle

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "04-code" / "designlab"))
import figlib as fl  # noqa: E402

rows = (("Frontier for all", 0.00931, "priced, not run", "policy", "//"),
        ("Gated rule", 0.00173, "37/40, 0 high-risk on small", "verified", ""),
        ("Cost-only rule", 0.00028, "37/40, 20 high-risk on small: fails the floor", "fail", "xx"))
fig, ax = fl.figure(4.5, 3.0)
n = len(rows)
for i, (name, cost, lab, tok, h) in enumerate(rows):
    y = n - 1 - i
    ax.barh(y, cost * 1000, color=fl.FILL[tok], edgecolor=fl.C[tok], hatch=h, lw=0.75,
            height=0.6)
    ax.text(cost * 1000 + 0.15, y, f"${cost:.5f}", va="center", fontsize=9, color=fl.INK)
    ax.text(0.1, y - 0.42, lab, va="center", fontsize=9, color=fl.LABEL[tok])
ax.set_yticks(range(n))
ax.set_yticklabels([r[0] for r in reversed(rows)], fontsize=9)
ax.set_xlim(0, 12.5)
ax.set_ylim(-0.8, n - 0.4)
ax.set_xlabel("Cost per task (tenths of a cent)")
fl.save(fig)
