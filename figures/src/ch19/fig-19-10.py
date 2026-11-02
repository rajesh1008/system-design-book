"""Figure 19.10  Evaluating retrieval for agents.

Reading order: top to bottom, from the ranked list to the outcome. Each
row is one layer of the evaluation, the question it answers, and
Lakeshore's value for May 18 to 31, 2026 (Lakeshore figures are
illustrative). The highlighted row is grounding, the number the agent's
consumer depends on.
"""
import figlib as fl
from matplotlib.patches import Rectangle

rows = [("List", "Right page in top 10?", "89%"),
        ("Currency", "Stale page first?", "0"),
        ("Loop", "Queries per task", "Median 3"),
        ("Hand-off", "Given back", "About 4%"),
        ("Grounding", "Claims cited\nand in effect", "94%"),
        ("Audit", "Person agrees", "96%")]
hi = 4

fig, ax = fl.figure(4.5, 3.6)
ax.set_xlim(0, 6.6)
ax.set_ylim(0, len(rows) + 1)
ax.axis("off")
for x, h in ((0.05, "Layer"), (1.45, "Question"), (4.6, "May 18-31")):
    ax.text(x, len(rows) + 0.45, h, ha="left", va="center", fontsize=9.5,
            fontweight="bold")
for i, (name, qn, val) in enumerate(rows):
    y = len(rows) - 1 - i
    tok = "verified" if i == hi else "knowledge"
    ax.add_patch(Rectangle((4.5, y + 0.1), 2.05, 0.8,
                           facecolor=fl.FILL[tok], edgecolor=fl.C[tok],
                           lw=1.8 if i == hi else 0.6))
    ax.text(0.05, y + 0.5, name, ha="left", va="center", fontsize=9.5,
            fontweight="bold" if i == hi else "normal")
    ax.text(1.45, y + 0.5, qn, ha="left", va="center", fontsize=9.5,
            color=fl.INK)
    ax.text(4.6, y + 0.5, val, ha="left", va="center", fontsize=9.5,
            color=fl.LABEL[tok], fontweight="bold")
fl.save(fig)
