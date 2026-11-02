"""Figure 10.10  The estimate on one page.

Reading order: one row per number, top to bottom: the question on the
left, the answer on the right. The emphasized row is the one Sarah
signed. Values from python3 -m capacity.demo (seed 10).
"""
from matplotlib.patches import Rectangle

import figlib as fl

rows = [("Sessions open, Monday surge", "420"),
        ("Model slots", "8"),
        ("Input tokens a minute", "1.3 million"),
        ("Task p95 against 40 s", "37.7 s"),
        ("Handed to a person", "1.23%"),
        ("Storm requests a second", "27.3"),
        ("Storm reviewers", "about 75")]
EMPH = 3
fig, ax = fl.figure(4.5, 3.6)
n = len(rows)
ax.set_xlim(0, 4)
ax.set_ylim(-0.2, n + 0.9)
ax.axis("off")
ax.text(1.35, n + 0.45, "Question", ha="center", va="center",
        fontsize=10, fontweight="bold", color=fl.INK)
ax.text(3.3, n + 0.45, "Answer", ha="center", va="center", fontsize=10,
        fontweight="bold", color=fl.INK)
for i, (q, a) in enumerate(rows):
    y = n - 1 - i
    em = i == EMPH
    ax.add_patch(Rectangle((0.02, y + 0.1), 2.66, 0.8,
                           facecolor=fl.FILL["ops"], edgecolor=fl.C["ops"],
                           lw=0.75))
    ax.text(1.35, y + 0.5, q, ha="center", va="center", fontsize=9.5,
            color=fl.LABEL["ops"])
    ax.add_patch(Rectangle((2.75, y + 0.1), 1.2, 0.8,
                           facecolor=fl.FILL["verified"] if em else "white",
                           edgecolor=fl.INK if em else fl.GREY_DARK,
                           lw=2.5 if em else 0.75))
    ax.text(3.35, y + 0.5, a, ha="center", va="center", fontsize=10,
            fontweight="bold" if em else "normal", color=fl.INK)
fl.save(fig)
