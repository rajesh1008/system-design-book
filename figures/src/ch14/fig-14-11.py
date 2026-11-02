"""Figure 14.11  The self-host decision table, April 28, 2026.

Reading order: one row per option, top to bottom; the kept option is
emphasized. Values from serving.demo --part tco (April volume of
20,100 tasks, contract prices, 78% hit, $3.20 a GPU-hour).
"""
import sys
from pathlib import Path

from matplotlib.patches import Rectangle

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "04-code" / "designlab"))
import figlib as fl  # noqa: E402

rows = (("API, frontier steps", "$1,573", "Pinned frontier", "Keep", True),
        ("API, small steps", "$52", "Small model", "Keep", False),
        ("Self-host 8B-class,\n2 GPUs", "$12,672", "1.2% busy", "Defer", False),
        ("Self-host frontier,\n16 GPUs", "$53,376", "Unproven", "Defer", False))
cols = (0.0, 1.55, 2.45, 3.75)
heads = ("Option", "A month", "Quality", "Decision")
fig, ax = fl.figure(4.5, 3.5)
n = len(rows)
ax.set_xlim(0, 4.6)
ax.set_ylim(-0.75, n + 0.9)
ax.axis("off")
for x, h in zip(cols, heads):
    ax.text(x + 0.05, n + 0.45, h, va="center", fontsize=10,
            fontweight="bold", color=fl.INK)
for i, (opt, cost, q, dec, keep) in enumerate(rows):
    y = n - 1 - i
    tok = "verified" if dec == "Keep" else "policy"
    ax.add_patch(Rectangle((0.0, y + 0.06), 4.6, 0.88,
                           facecolor=fl.FILL[tok],
                           edgecolor=fl.INK if keep else fl.C[tok],
                           lw=2.5 if keep else 0.75))
    for x, t in zip(cols, (opt, cost, q, dec)):
        ax.text(x + 0.05, y + 0.5, t, va="center", fontsize=9.5,
                color=fl.INK, fontweight="bold" if x == cols[3] else None)
ax.text(0.05, -0.4, "Revisit at 100,000 tasks a month", fontsize=9.5, color=fl.INK, style="italic")
fl.save(fig)
