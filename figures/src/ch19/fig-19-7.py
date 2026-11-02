"""Figure 19.7  Queries per task.

Reading order: left to right. Each bar is the share of research tasks
from May 18 to 31, 2026, that issued that many queries under a budget
of eight (Lakeshore figures are illustrative). The median is three. The
dashed line is the budget; the April 29 shadow loop, at 41 queries,
would sit far off the right edge.
"""
import figlib as fl

n = list(range(1, 9))
share = [15, 25, 21, 13, 9, 8, 4, 5]

fig, ax = fl.figure(4.5, 3.1)
cols = [fl.FILL["knowledge"]] * 8
bars = ax.bar(n, share, width=0.7, color=cols,
              edgecolor=fl.C["knowledge"], linewidth=1.0)
bars[2].set_edgecolor(fl.C["ops"])
bars[2].set_linewidth(2.0)
for x, s in zip(n, share):
    ax.text(x, s + 0.5, f"{s}%", ha="center", va="bottom", fontsize=9.5,
            color=fl.INK)
ax.axvline(8.5, color=fl.C["ops"], linestyle="--", linewidth=1.2)
ax.text(8.4, 23, "budget 8", ha="right", va="center", fontsize=9.5,
        color=fl.LABEL["ops"])
ax.text(3.4, 22.5, "median 3", ha="left", va="bottom", fontsize=9.5,
        color=fl.LABEL["ops"])
ax.text(8.4, 17.5, "April 29: 41,\noff scale", ha="right",
        va="center", fontsize=9.5, color=fl.INK)
ax.set_xticks(n)
ax.set_xlabel("Queries issued by one task")
ax.set_ylabel("Share of tasks (%)")
ax.set_ylim(0, 30)
ax.set_xlim(0.4, 8.8)
ax.spines[["top", "right"]].set_visible(False)
fl.save(fig)
