"""Figure 41.8  What the team must not become.

Reading order: one row per failure shape, top to bottom: what the team
turns into, the sign that shows it early, and the check in org that
catches it. All rows are failures, drawn in coral; the third column is
the guard. From section 8 (Lakeshore figures are illustrative).
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "04-code" / "designlab"))
import figlib as fl  # noqa: E402
from matplotlib.patches import Rectangle  # noqa: E402

rows = (("Ticket queue", "Requests, no owners", "One owner each"),
        ("Rule author", "Team edits rules", "Author never signs"),
        ("Only approver", "All keys on team", "Partner owners"),
        ("Model shop", "Hires for models", "Gap check"),
        ("Meeting series", "Forums decide little", "Rhythm check"),
        ("Shadow ops desk", "Team tells customers", "Message owner"))
heads = ("Becomes", "Early sign", "Guard in org")
cols = (0.0, 1.55, 3.4)
fig, ax = fl.figure(4.5, 3.0)
n = len(rows)
W = 5.0
ax.set_xlim(0, W)
ax.set_ylim(-0.1, n + 0.9)
ax.axis("off")
for x, h in zip(cols, heads):
    ax.text(x + 0.05, n + 0.45, h, va="center", fontsize=9.5,
            fontweight="bold", color=fl.INK)
for i, cells in enumerate(rows):
    y = n - 1 - i
    ax.add_patch(Rectangle((0.0, y + 0.06), cols[2] - 0.05, 0.88,
                           facecolor=fl.FILL["fail"], edgecolor=fl.C["fail"],
                           lw=0.75))
    ax.add_patch(Rectangle((cols[2], y + 0.06), W - cols[2], 0.88,
                           facecolor=fl.FILL["org"], edgecolor=fl.C["org"],
                           lw=0.75))
    for x, s in zip(cols, cells):
        ax.text(x + 0.05, y + 0.5, s, va="center", fontsize=9,
                color=fl.INK, fontweight="bold" if x == cols[0] else None)
fl.save(fig)
