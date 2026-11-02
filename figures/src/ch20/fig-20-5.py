"""Figure 20.5  Estimated against actual bytes.

Reading order: left to right. Each bar counts answered queries in the
replayed week of May 21 to 31, 2026, whose estimate was above 10 MB,
by the ratio of estimated to actual bytes (designlab, seed 20). Most
estimates run a little low, from 0.83 to 1.03; the median is 0.94. The
marker shows the opening year scan at 0.91.
"""
import figlib as fl

bins = [0.82, 0.84, 0.86, 0.88, 0.90, 0.92, 0.94, 0.96, 0.98, 1.00, 1.02]
count = [27, 45, 26, 4, 17, 32, 85, 58, 21, 12, 5]

fig, ax = fl.figure(4.5, 3.2)
ax.bar([b + 0.01 for b in bins], count, width=0.017,
       color=fl.FILL["knowledge"], edgecolor=fl.C["knowledge"], lw=1.0)
ax.axvline(1.0, color=fl.INK, lw=0.75, ls="--")
ax.text(1.003, 80, "estimate\n= actual", fontsize=9, color=fl.INK)
ax.axvline(0.91, color=fl.C["fail"], lw=1.5)
ax.text(0.905, 92, "year scan, 0.91", fontsize=9, ha="right",
        color=fl.LABEL["fail"])
ax.text(0.945, 87, "median 0.94", fontsize=9, ha="center",
        color=fl.LABEL["knowledge"], va="bottom")
ax.set_xlabel("Estimated / actual bytes")
ax.set_ylabel("Answered queries")
ax.set_xlim(0.8, 1.06)
ax.set_ylim(0, 100)
ax.spines[["top", "right"]].set_visible(False)
fl.save(fig)
