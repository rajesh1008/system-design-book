"""Figure 22.5  Scope and access by role.

Reading order: one row per role, columns for what it may read. Values
from memory.policy.READ_POLICY; every role reads its own tenant only.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "04-code" / "designlab"))
import figlib as fl  # noqa: E402
from matplotlib.patches import Rectangle  # noqa: E402

rows = (("Agent loop", "Yes", "No", "No"),
        ("Agent desk", "Yes", "Yes", "Yes"),
        ("Privacy office", "Yes", "Yes", "Yes"),
        ("Analytics", "No", "No", "No"))
cols = (0.0, 1.3, 2.5, 3.6)
heads = ("Role", "Preferences", "Health,\nconsent", "History")
fig, ax = fl.figure(4.5, 3.0)
n = len(rows)
ax.set_xlim(0, 4.6)
ax.set_ylim(-0.1, n + 0.9)
ax.axis("off")
for x, h in zip(cols, heads):
    ax.text(x + 0.05, n + 0.45, h, va="center", fontsize=10,
            fontweight="bold", color=fl.INK)
for i, row in enumerate(rows):
    y = n - 1 - i
    ax.add_patch(Rectangle((0.0, y + 0.06), 4.6, 0.88, facecolor="white",
                           edgecolor=fl.C["knowledge"], lw=0.75))
    for j, (x, t) in enumerate(zip(cols, row)):
        if j and t == "No":
            ax.add_patch(Rectangle((x, y + 0.16), 0.9, 0.68,
                                   facecolor=fl.FILL["policy"],
                                   edgecolor=fl.C["policy"], lw=0.75))
        ax.text(x + 0.08, y + 0.5, t, va="center", fontsize=9.5,
                color=fl.INK, fontweight="bold" if j == 0 else None)
ax.text(0.05, -0.05, "Tenant comes from the session token",
        fontsize=9.5, color=fl.INK, va="top")
fl.save(fig)
