"""Figure 18.3  The five levers.

Reading order: one row per lever, top to bottom, widest effect on the
model line first. Ranges are model cost per attempt from the worse to
the better setting. From cost.demo --part levers.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "04-code" / "designlab"))
import figlib as fl  # noqa: E402
from matplotlib.patches import Rectangle  # noqa: E402

rows = (("Model mix", "Model per step", "63% small", "$0.072-0.015", "model"),
        ("Cache", "Repeated prefix", "78% hit", "$0.060-0.020", "knowledge"),
        ("Tokens", "Prompt size", "As built", "$0.031-0.020", "ops"),
        ("Steps", "Calls a task", "Caps on", "$0.030-0.024", "ops"),
        ("Retries", "Error repeats", "As run", "$0.026-0.025", "ops"))
cols = (0.0, 0.95, 2.35, 3.35)
heads = ("Lever", "Changes", "May", "Model $/attempt")
fig, ax = fl.figure(4.5, 3.4)
n = len(rows)
ax.set_xlim(0, 4.6)
ax.set_ylim(-0.1, n + 0.9)
ax.axis("off")
for x, h in zip(cols, heads):
    ax.text(x + 0.05, n + 0.45, h, va="center", fontsize=10,
            fontweight="bold", color=fl.INK)
for i, (lev, what, may, rng, tok) in enumerate(rows):
    y = n - 1 - i
    fill = fl.C["model"] if tok == "model" else fl.FILL[tok]
    ax.add_patch(Rectangle((0.0, y + 0.06), 0.9, 0.88, facecolor=fill,
                           edgecolor=fl.C[tok], lw=0.75))
    ax.text(0.05, y + 0.5, lev, va="center", fontsize=9.5,
            color="#FFFFFF" if tok == "model" else fl.INK,
            fontweight="bold")
    for x, t in zip(cols[1:], (what, may, rng)):
        ax.text(x + 0.05, y + 0.5, t, va="center", fontsize=9.5,
                color=fl.INK)
fl.save(fig)
