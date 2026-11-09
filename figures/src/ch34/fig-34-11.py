"""Figure 34.11  What the sibling owns.

Reading order: one row per topic, top to bottom: the topic, what
this book covers, and what the sibling volume, AI Evals in
Practice, takes to depth.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "04-code" / "designlab"))
import figlib as fl  # noqa: E402
from matplotlib.patches import Rectangle  # noqa: E402

rows = (("Golden sets", "The gate's set", "Sampling, coverage"),
        ("Trajectories", "Match rule", "Rubrics, partial credit"),
        ("Judges", "Wording, calibrated", "Prompt design, bias"),
        ("Statistics", "pass^k, kappa", "Intervals, power"),
        ("Online", "Signals, sample", "Experiments, drift"),
        ("Labeling", "One owner", "Guides, agreement"))
cols = (0.0, 1.45, 2.95)
heads = ("Topic", "This book", "The sibling")
fig, ax = fl.figure(4.5, 3.0)
n = len(rows)
ax.set_xlim(0, 4.6)
ax.set_ylim(-0.1, n + 0.9)
ax.axis("off")
for x, h in zip(cols, heads):
    ax.text(x + 0.05, n + 0.45, h, va="center", fontsize=10,
            fontweight="bold", color=fl.INK)
for i, r in enumerate(rows):
    y = n - 1 - i
    ax.add_patch(Rectangle((0.0, y + 0.06), 4.6, 0.88,
                           facecolor=fl.FILL["org"], edgecolor=fl.C["org"],
                           lw=0.75))
    for j, (x, v) in enumerate(zip(cols, r)):
        ax.text(x + 0.05, y + 0.5, v, va="center", fontsize=9.5,
                color=fl.INK, fontweight="bold" if j == 0 else None)
fl.save(fig)
