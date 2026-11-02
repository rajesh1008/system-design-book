"""Figure 19.8  Grounding by budget.

Reading order: left to right, budget on a log scale. The solid line is
the share of claims grounded when a loop that runs out of budget answers
anyway; the dashed line is the same loop handing off instead. Values
are the lab's forty desk tasks. Past three queries the solid line is
flat, so more budget buys only more queries on questions the corpus
cannot answer.
"""
import figlib as fl

budget = [1, 2, 3, 4, 6, 8, 12, 20]
anyway = [72, 86, 91, 91, 91, 91, 91, 91]
handoff = [100] * 8

fig, ax = fl.figure(4.5, 3.1)
ax.plot(budget, handoff, linestyle="--", marker="s", markersize=4,
        color=fl.C["verified"], linewidth=1.5)
ax.plot(budget, anyway, linestyle="-", marker="o", markersize=4,
        color=fl.C["fail"], linewidth=1.5)
ax.set_xscale("log")
ax.set_xticks(budget)
ax.set_xticklabels([str(b) for b in budget])
ax.minorticks_off()
fl.label_line(ax, 20, 100, "hand off", color=fl.LABEL["verified"], dy=-8)
fl.label_line(ax, 20, 91, "answer anyway", color=fl.LABEL["fail"], dy=-8)
ax.annotate("knee at 3", xy=(3, 91), xytext=(1.6, 80), fontsize=9.5,
            color=fl.INK, arrowprops=dict(arrowstyle="->", color=fl.INK,
                                          lw=0.8))
ax.set_xlabel("Query budget per task (log scale)")
ax.set_ylabel("Claims grounded (%)")
ax.set_ylim(65, 104)
ax.set_xlim(0.85, 34)
ax.spines[["top", "right"]].set_visible(False)
fl.save(fig)
