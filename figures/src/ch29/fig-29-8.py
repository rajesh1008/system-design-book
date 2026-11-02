"""Figure 29.8  Permissions for code and interfaces.

Reading order: one row per actor, top to bottom; what it may do and
what it may not. From sandbox.gate and sandbox.browser.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "04-code" / "designlab"))
import figlib as fl  # noqa: E402
from matplotlib.patches import Rectangle  # noqa: E402

rows = (("Code run", "Own directory,\nlisted hosts", "Secrets, host,\nnext run", "ops"),
        ("Coding agent", "Push agent/*,\nopen proposal", "Merge, approve,\nedit owners", "knowledge"),
        ("Browser reader", "Read listed\nportals", "Submit, other\nhosts", "evidence"),
        ("Merge service", "Merge approved\nhead", "Merge stale\napproval", "policy"))
cols = (0.0, 1.45, 3.0)
heads = ("Actor", "May", "May not")
fig, ax = fl.figure(4.5, 3.0)
n = len(rows)
ax.set_xlim(0, 4.6)
ax.set_ylim(-0.1, n + 0.9)
ax.axis("off")
for x, h in zip(cols, heads):
    ax.text(x + 0.05, n + 0.45, h, va="center", fontsize=10,
            fontweight="bold", color=fl.INK)
for i, (a, may, no, tok) in enumerate(rows):
    y = n - 1 - i
    ax.add_patch(Rectangle((0.0, y + 0.06), 4.6, 0.88,
                           facecolor=fl.FILL[tok], edgecolor=fl.C[tok],
                           lw=0.75))
    for x, t in zip(cols, (a, may, no)):
        ax.text(x + 0.05, y + 0.5, t, va="center", fontsize=9,
                color=fl.INK, fontweight="bold" if x == cols[0] else None)
fl.save(fig)
