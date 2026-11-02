"""Figure 30.1  What an SDK decides for you.

Reading order: one row per decision, top to bottom; what the SDK does
by default and what Lakeshore's harness sets instead. From the
servicing manifest (Chapter 25) and runtimes.portability.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "04-code" / "designlab"))
import figlib as fl  # noqa: E402
from matplotlib.patches import Rectangle  # noqa: E402

rows = (("Loop shape", "Its loop", "Manifest, loop", "model"),
        ("State", "Messages,\nposition", "Run store", "ops"),
        ("Tool call", "In-process\nhook", "Gateway and\npolicy engine", "model"),
        ("Retry", "Re-run\nthe step", "Effect key", "ops"),
        ("Context", "Append, trim", "Context policy", "model"),
        ("Tracing", "Its tracer", "Trail line", "ops"))
cols = (0.0, 1.45, 3.0)
heads = ("Decision", "SDK default", "Lakeshore sets")
fig, ax = fl.figure(4.5, 3.0)
n = len(rows)
ax.set_xlim(0, 4.6)
ax.set_ylim(-0.1, n + 0.9)
ax.axis("off")
for x, h in zip(cols, heads):
    ax.text(x + 0.05, n + 0.45, h, va="center", fontsize=10,
            fontweight="bold", color=fl.INK)
for i, (a, b, c, tok) in enumerate(rows):
    y = n - 1 - i
    ax.add_patch(Rectangle((0.0, y + 0.06), 4.6, 0.88,
                           facecolor=fl.FILL[tok], edgecolor=fl.C[tok],
                           lw=0.75))
    for x, t in zip(cols, (a, b, c)):
        ax.text(x + 0.05, y + 0.5, t, va="center", fontsize=9,
                color=fl.INK, linespacing=0.95,
                fontweight="bold" if x == cols[0] else None)
fl.save(fig)
