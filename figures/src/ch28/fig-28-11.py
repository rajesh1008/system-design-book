"""Figure 28.11  The loop linter result, June 29, 2026.

Reading order: one row per loop spec, top to bottom: properties
passed of seven, then the first failing property. Values from
loops.demo --part lint. Lakeshore figures are illustrative.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "04-code" / "designlab"))
import figlib as fl  # noqa: E402
from matplotlib.patches import Rectangle  # noqa: E402

rows = (("Fare watch 1.0.0", "1 of 7", "six", "fail"),
        ("Fare watch 1.1.0", "7 of 7", "none", "verified"),
        ("Waiver watch", "7 of 7", "none", "verified"),
        ("Model stop", "6 of 7", "stop", "fail"),
        ("No state", "6 of 7", "state", "fail"),
        ("Self-verify", "6 of 7", "verify", "fail"))
cols = (0.0, 2.0, 3.05)
heads = ("Spec", "Passed", "Fails")
fig, ax = fl.figure(4.5, 3.0)
n = len(rows)
ax.set_xlim(0, 4.6)
ax.set_ylim(-0.1, n + 0.9)
ax.axis("off")
for x, h in zip(cols, heads):
    ax.text(x + 0.05, n + 0.45, h, va="center", fontsize=10,
            fontweight="bold", color=fl.INK)
for i, (spec, ok, bad, tok) in enumerate(rows):
    y = n - 1 - i
    ax.add_patch(Rectangle((0.0, y + 0.06), 4.6, 0.88,
                           facecolor=fl.FILL[tok], edgecolor=fl.C[tok],
                           lw=0.75))
    for x, t in zip(cols, (spec, ok, bad)):
        ax.text(x + 0.07, y + 0.5, t, va="center", fontsize=9.5,
                color=fl.INK, fontweight="bold" if x == cols[1] else None)
fl.save(fig)
