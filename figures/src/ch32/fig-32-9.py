"""Figure 32.9  The identity scorecard.

Reading order: one row per measure, top to bottom; the value on
June 16 and on Monday, June 29, 2026. Standing privileges is the cell
the card turns on. Values from the identity card and the lab.
Lakeshore figures are illustrative.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "04-code" / "designlab"))
import figlib as fl  # noqa: E402
from matplotlib.patches import Rectangle  # noqa: E402

rows = (("Runs with their\nown credential", "0%", "100%", "verified"),
        ("Credential reach", "Every customer", "1 itinerary", "verified"),
        ("Credential lifetime", "Never expires", "15 minutes", "verified"),
        ("Standing privileges", "8 scopes", "0", "policy"),
        ("Trail lines signed,\npermission bound", "None", "100%", "verified"),
        ("Card or document\nnumbers, replay", "Not tested", "0 of 200", "verified"))
cols = (0.0, 1.75, 3.15)
heads = ("Measure", "June 16", "June 29")
fig, ax = fl.figure(4.5, 3.2)
n = len(rows)
ax.set_xlim(0, 4.6)
ax.set_ylim(-0.1, n + 0.9)
ax.axis("off")
for x, h in zip(cols, heads):
    ax.text(x + 0.05, n + 0.45, h, va="center", fontsize=10,
            fontweight="bold", color=fl.INK)
for i, (*cells, tok) in enumerate(rows):
    y = n - 1 - i
    ax.add_patch(Rectangle((0.0, y + 0.06), 4.6, 0.88,
                           facecolor="white", edgecolor=fl.GREY_LIGHT,
                           lw=0.75))
    ax.add_patch(Rectangle((cols[2], y + 0.06), 4.6 - cols[2], 0.88,
                           facecolor=fl.FILL[tok], edgecolor=fl.C[tok],
                           lw=2.0 if tok == "policy" else 0.75))
    for x, t in zip(cols, cells):
        ax.text(x + 0.05, y + 0.5, t, va="center", fontsize=9,
                color=fl.INK, fontweight="bold" if x == cols[0] else None)
fl.save(fig)
