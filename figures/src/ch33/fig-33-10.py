"""Figure 33.10  What the sibling owns.

Reading order: one row per topic, top to bottom; what this chapter
covers and where the security book goes deeper.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "04-code" / "designlab"))
import figlib as fl  # noqa: E402
from matplotlib.patches import Rectangle  # noqa: E402

rows = (("Red teaming", "Battery\nper release", "Adaptive\ncampaigns", "org"),
        ("Detection", "A signal", "Classifier design", "org"),
        ("Identity", "Delegated identity", "Token exchange", "org"),
        ("Supply chain", "Review, hash", "Signing", "org"),
        ("Response", "Trail inputs", "Forensics, law", "org"))
cols = (0.0, 1.2, 2.85)
heads = ("Topic", "This chapter", "Sibling book")
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

