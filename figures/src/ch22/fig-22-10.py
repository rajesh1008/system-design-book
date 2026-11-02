"""Figure 22.10  The memory scorecard, May 15, 2026.

Reading order: one row per line, top to bottom. Values from the
memory.demo shadow run and Owen Fletcher's policy test; the last row
is the open number from the legacy audit.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "04-code" / "designlab"))
import figlib as fl  # noqa: E402
from matplotlib.patches import Rectangle  # noqa: E402

rows = (("New writes with\nsource and scope", "100%", "Daniel Price", "verified"),
        ("Supersession", "Tested", "Ben Carter", "verified"),
        ("Memories used\nas authority", "0", "Owen Fletcher", "verified"),
        ("Legacy notes\nwithout a source", "35 of 349", "Rachel Morgan", "knowledge"))
cols = (0.0, 1.75, 3.0)
heads = ("Line", "Value", "Owner")
fig, ax = fl.figure(4.5, 3.0)
n = len(rows)
ax.set_xlim(0, 4.6)
ax.set_ylim(-0.1, n + 0.9)
ax.axis("off")
for x, h in zip(cols, heads):
    ax.text(x + 0.05, n + 0.45, h, va="center", fontsize=10,
            fontweight="bold", color=fl.INK)
for i, (line, val, own, tok) in enumerate(rows):
    y = n - 1 - i
    ax.add_patch(Rectangle((0.0, y + 0.06), 4.6, 0.88,
                           facecolor=fl.FILL[tok], edgecolor=fl.C[tok],
                           lw=0.75))
    for x, t in zip(cols, (line, val, own)):
        ax.text(x + 0.05, y + 0.5, t, va="center", fontsize=9.5,
                color=fl.INK, fontweight="bold" if x == cols[1] else None)
fl.save(fig)
