"""Figure 19.3  Late interaction compared with single-vector.

Reading order: one row per property, single-vector on the left and late
interaction on the right. The last row is the decision for Lakeshore's
fare rules in May 2026, which is why it is highlighted.
"""
import figlib as fl
from matplotlib.patches import Rectangle

rows = [("Stored", "One vector", "Many vectors"),
        ("Scoring", "One dot product", "Best match\nper query token"),
        ("Index", "Smallest", "Several times\nlarger"),
        ("Wins on", "Short queries", "Long, rare-term\nqueries"),
        ("Lakeshore", "Adopted, with\nlexical", "Not yet;\ntrigger set")]
hi = len(rows) - 1

fig, ax = fl.figure(4.5, 3.6)
ax.set_xlim(0, 6.6)
ax.set_ylim(0, len(rows) + 1)
ax.axis("off")
for x, h in ((0.05, "Property"), (1.95, "Single vector"), (4.25, "Late interaction")):
    ax.text(x, len(rows) + 0.45, h, ha="left", va="center", fontsize=9.5,
            fontweight="bold")
for i, (name, a, b) in enumerate(rows):
    y = len(rows) - 1 - i
    for x0, tok in ((1.85, "knowledge"), (4.15, "model")):
        ax.add_patch(Rectangle((x0, y + 0.08), 2.2, 0.84,
                               facecolor=fl.FILL[tok] if (i != hi and tok == "knowledge") else "white",
                               edgecolor=fl.C[tok],
                               lw=1.8 if i == hi else 0.6))
    ax.text(0.05, y + 0.5, name, ha="left", va="center", fontsize=9.5,
            fontweight="bold" if i == hi else "normal")
    ax.text(1.95, y + 0.5, a, ha="left", va="center", fontsize=9.5,
            color=fl.INK)
    ax.text(4.25, y + 0.5, b, ha="left", va="center", fontsize=9.5,
            color=fl.INK)
fl.save(fig)
