"""Figure 1.4  What the demo log shows and what it cannot answer.

Reading order: one row per question, top to bottom; the middle column is
the demo log's answer, the right column is the record that would answer.
"""
import figlib as fl
from matplotlib.patches import Rectangle

rows = [
    ("Was the tool called?", True, "tool_call line"),
    ("Who allowed it?", False, "permission"),
    ("Under which policy?", False, "policy version"),
    ("Was the retry new?", False, "idempotency key"),
    ("Did it happen once?", False, "reconciler"),
]
fig, ax = fl.figure(4.5, 3.0)
ax.set_xlim(0, 10.6)
ax.set_ylim(0, len(rows) + 1)
ax.axis("off")
head_y = len(rows) + 0.5
for x, text in ((0.1, "Question"), (4.15, "Demo log"), (6.4, "Needs")):
    ax.text(x, head_y, text, fontweight="bold", va="center")
for i, (q, ok, rec) in enumerate(rows):
    y = len(rows) - i - 0.5
    tok = "ops" if ok else "fail"
    ax.add_patch(Rectangle((4.15, y - 0.36), 1.7, 0.72, facecolor=fl.FILL[tok],
                           edgecolor=fl.C[tok], lw=fl.STROKE["data"],
                           hatch="" if ok else "///"))
    ax.text(0.1, y, q, va="center")
    ax.text(5.0, y, "yes" if ok else "no", va="center", ha="center",
            color=fl.LABEL[tok], fontweight="bold",
            bbox=dict(facecolor="white", edgecolor="none", pad=1.5))
    ax.text(6.4, y, rec, va="center", color=fl.LABEL["evidence"], **fl.mono(rec))
    ax.plot([0, 10.6], [y - 0.5, y - 0.5], color=fl.GREY_LIGHT, lw=0.5,
            linestyle="-", marker="")
fl.save(fig)
