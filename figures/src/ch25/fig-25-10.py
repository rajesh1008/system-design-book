"""Figure 25.10  Harness against model responsibilities.

Reading order: one row per responsibility; a filled box marks who owns
it. The model owns judgment inside a step; the harness owns everything
that decides what a step may see, do, and count as finished.
"""
import figlib as fl
from matplotlib.patches import Rectangle

rows = [("Read the customer", "model"),
        ("Choose the next step", "model"),
        ("Word the reply", "model"),
        ("What the step may see", "ops"),
        ("Which tools exist", "ops"),
        ("When the case stops", "ops"),
        ("Whether it happened", "ops"),
        ("How much it may spend", "ops")]

fig, ax = fl.figure(4.8, 3.6)
ax.set_xlim(0, 7.0)
ax.set_ylim(0, len(rows) + 1)
ax.axis("off")
for x, h in ((0.05, "Responsibility"), (4.25, "Model"), (5.65, "Harness")):
    ax.text(x, len(rows) + 0.45, h, ha="left", va="center", fontsize=9.5,
            fontweight="bold")
for i, (name, owner) in enumerate(rows):
    y = len(rows) - 1 - i
    ax.text(0.05, y + 0.5, name, ha="left", va="center", fontsize=9.5,
            color=fl.INK)
    for x0, tok in ((4.15, "model"), (5.55, "ops")):
        on = tok == owner
        ax.add_patch(Rectangle((x0, y + 0.12), 1.2, 0.76,
                               facecolor=fl.FILL[tok] if on else "white",
                               edgecolor=fl.C[tok], lw=1.2 if on else 0.5))
        if on:
            ax.text(x0 + 0.6, y + 0.5, "owns", ha="center", va="center",
                    fontsize=9, color=fl.TEXT_ON[tok], fontweight="bold")
fl.save(fig)
