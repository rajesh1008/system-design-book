"""Figure 20.8  Graph or layer, by question.

Reading order: top to bottom. Each row is a kind of question; the
right column names the store that answers it. Counts and rates go to
the layer; who is connected to what goes to the graph; who may act
goes to the grant, which neither store holds.
"""
import figlib as fl
from matplotlib.patches import Rectangle

rows = [("How many, how much", "Semantic layer", "knowledge"),
        ("Trend over weeks or months", "Semantic layer", "knowledge"),
        ("Which bookings share a flight", "Graph", "ops"),
        ("How two records connect", "Graph", "ops"),
        ("A one-off join, once", "An analyst", "org"),
        ("May this person change it", "The grant", "policy")]

fig, ax = fl.figure(4.5, 3.0)
ax.set_xlim(0, 6.4)
ax.set_ylim(0, len(rows) + 1)
ax.axis("off")
for x, h in ((0.05, "Question"), (3.75, "Answered by")):
    ax.text(x, len(rows) + 0.45, h, ha="left", va="center", fontsize=9.5,
            fontweight="bold")
for i, (q, by, tok) in enumerate(rows):
    y = len(rows) - 1 - i
    last = tok == "policy"
    ax.add_patch(Rectangle((3.65, y + 0.12), 2.7, 0.76,
                           facecolor=fl.FILL[tok], edgecolor=fl.C[tok],
                           lw=1.6 if last else 0.6))
    ax.text(0.05, y + 0.5, q, ha="left", va="center", fontsize=9,
            fontweight="bold" if last else "normal")
    ax.text(3.75, y + 0.5, by, ha="left", va="center", fontsize=9,
            color=fl.LABEL[tok], fontweight="bold")
fl.save(fig)
