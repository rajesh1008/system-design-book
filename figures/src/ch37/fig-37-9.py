"""Figure 37.9  The reliability card.

Reading order: one row per line of the card, top to bottom: the line,
its reading on Monday, August 31, 2026, and who answers for it. From
reliability.card (Lakeshore figures are illustrative).
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "04-code" / "designlab"))
import figlib as fl  # noqa: E402
from matplotlib.patches import Rectangle  # noqa: E402
from reliability import card  # noqa: E402

text = {"objectives": "5, none written by the agent",
        "error budget": None, "incidents": "2 in July", "time to stop": None}
rows = []
for k, v, who in card.card():
    if k == "error budget":
        v = "Rebooking " + v.split("rebooking ")[1]
    elif k == "time to stop":
        v = v.replace("median", "Median")
    else:
        v = text[k]
    rows.append((k.capitalize(), v, who))
fig, ax = fl.figure(4.5, 3.0)
n = len(rows)
ax.set_xlim(0, 4.75)
ax.set_ylim(-0.1, n + 0.8)
ax.axis("off")
for x, h in zip((0.0, 1.15, 3.6), ("Line", "August 31", "Answers")):
    ax.text(x + 0.05, n + 0.4, h, va="center", fontsize=9.5,
            fontweight="bold", color=fl.INK)
for i, (k, v, who) in enumerate(rows):
    y = n - 1 - i
    tok = "verified" if k == "Error budget" else "ops"
    ax.add_patch(Rectangle((0.0, y + 0.06), 4.75, 0.88,
                           facecolor=fl.FILL[tok], edgecolor=fl.C[tok],
                           lw=1.5 if tok == "verified" else 0.75))
    ax.text(0.05, y + 0.5, k, va="center", fontsize=9, color=fl.INK,
            fontweight="bold")
    v = v if len(v) < 30 else v.replace(", read", ",\nread")
    ax.text(1.2, y + 0.5, v, va="center", fontsize=9, color=fl.INK)
    ax.text(3.65, y + 0.5, who, va="center", fontsize=9, color=fl.INK)
fl.save(fig)
