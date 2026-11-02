"""Figure 26.10  The tool scorecard, June 21, 2026.

Reading order: one row per line, top to bottom. Values from Owen
Fletcher's reconciliation of June 8 to 21, the registry decisions, and
Dr. Hannah Clarke's tool-error golden set of June 5. Lakeshore figures
are illustrative.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "04-code" / "designlab"))
import figlib as fl  # noqa: E402
from matplotlib.patches import Rectangle  # noqa: E402

rows = (("Tools behind\nthe gateway", "14", "Daniel Price", "verified"),
        ("Calls logged,\nJune 8 to 21", "100%", "Ben Carter", "verified"),
        ("Rejected at\nregistry review", "2", "Owen Fletcher", "policy"),
        ("Tool errors the\nagent resolved", "77%", "Hannah Clarke", "knowledge"))
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
