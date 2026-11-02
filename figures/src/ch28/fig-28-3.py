"""Figure 28.3  Stop conditions a machine can check.

Reading order: one row per stop, top to bottom: the stop, then what
checks it. The model may hand off; it never declares the run done.
Stops from loops.spec.FARE_WATCH.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "04-code" / "designlab"))
import figlib as fl  # noqa: E402
from matplotlib.patches import Rectangle  # noqa: E402

rows = (("Checked", "Gateway trail count", "verified"),
        ("Outcome", "Verifier, own read", "verified"),
        ("No progress", "Run store, five steps", "fail"),
        ("Oscillation", "Run store, A B A B", "fail"),
        ("Budget", "Budget enforcer", "policy"),
        ("Expired", "Watch end date", "ops"))
cols = (0.0, 1.75)
heads = ("Stop", "Checked by")
fig, ax = fl.figure(4.5, 3.0)
n = len(rows)
ax.set_xlim(0, 4.6)
ax.set_ylim(-0.1, n + 0.9)
ax.axis("off")
for x, h in zip(cols, heads):
    ax.text(x + 0.05, n + 0.45, h, va="center", fontsize=10,
            fontweight="bold", color=fl.INK)
for i, (stop, by, tok) in enumerate(rows):
    y = n - 1 - i
    ax.add_patch(Rectangle((0.0, y + 0.06), 4.6, 0.88,
                           facecolor=fl.FILL[tok], edgecolor=fl.C[tok],
                           lw=0.75))
    ax.text(0.07, y + 0.5, stop, va="center", fontsize=9.5,
            color=fl.INK, fontweight="bold")
    ax.text(cols[1] + 0.05, y + 0.5, by, va="center", fontsize=9.5,
            color=fl.INK)
fl.save(fig)
