"""Figure 31.5  Risk tiers by action.

Reading order: one row per action, top to bottom; the signed autonomy
ceiling and the tier the engine applies. From policy.tiers.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "04-code" / "designlab"))
import figlib as fl  # noqa: E402
from matplotlib.patches import Rectangle  # noqa: E402

rows = (("Refund", "With approval", "High: card", "policy"),
        ("Rebook", "Act and notify", "Medium: limits", "ops"),
        ("Credit, notify", "Act and notify", "Medium: limits", "ops"),
        ("Voucher", "Unattended", "Low: budget", "evidence"),
        ("Hotel cancel", "Suggest", "Person only", "org"))
cols = (0.0, 1.5, 3.0)
heads = ("Action", "Ceiling", "Tier")
fig, ax = fl.figure(4.5, 3.0)
n = len(rows)
ax.set_xlim(0, 4.6)
ax.set_ylim(-0.1, n + 0.9)
ax.axis("off")
for x, h in zip(cols, heads):
    ax.text(x + 0.05, n + 0.45, h, va="center", fontsize=10,
            fontweight="bold", color=fl.INK)
for i, (a, c, t, tok) in enumerate(rows):
    y = n - 1 - i
    ax.add_patch(Rectangle((0.0, y + 0.06), 4.6, 0.88,
                           facecolor=fl.FILL[tok], edgecolor=fl.C[tok],
                           lw=0.75))
    for x, s in zip(cols, (a, c, t)):
        ax.text(x + 0.05, y + 0.5, s, va="center", fontsize=9,
                color=fl.INK, fontweight="bold" if x == cols[0] else None)
fl.save(fig)
