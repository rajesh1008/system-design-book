"""Figure 33.2  Injection surfaces by plane.

Reading order: one row per plane, top to bottom; where attacker text
enters and the control at that surface. From threats.attacks.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "04-code" / "designlab"))
import figlib as fl  # noqa: E402
from matplotlib.patches import Rectangle  # noqa: E402

rows = (("Action", "Chat, letters,\nvoicemail", "Input contract", "ops"),
        ("Action", "Tool results", "Untagged (gap)", "fail"),
        ("Knowledge", "Notices, memory", "Fields, write gate", "knowledge"),
        ("Control", "Tool descriptions", "Review, hash", "policy"),
        ("Trail", "Text read later", "Digests only", "ops"))
cols = (0.0, 1.2, 2.85)
heads = ("Plane", "Surface", "Control")
H = 3.2
n = len(rows)
fig, ax = fl.figure(4.5, H)
ax.set_xlim(0, 4.6)
ax.set_ylim(-0.1, n + 0.9)
ax.axis("off")
for x, h in zip(cols, heads):
    ax.text(x + 0.05, n + 0.45, h, va="center", fontsize=10,
            fontweight="bold", color=fl.INK)
for i, row in enumerate(rows):
    y = n - 1 - i
    tok = row[-1]
    ax.add_patch(Rectangle((0.0, y + 0.06), 4.6, 0.88,
                           facecolor=fl.FILL[tok], edgecolor=fl.C[tok],
                           lw=0.75))
    for x, t in zip(cols, row[:-1]):
        ax.text(x + 0.05, y + 0.5, t, va="center", fontsize=9,
                color=fl.INK, fontweight="bold" if x == cols[0] else None)
fl.save(fig)

