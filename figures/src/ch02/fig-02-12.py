"""Figure 2.12  Duplicate refunds per 1,000 as late answers grow.

Reading order: left to right along the share of calls answered after
the 8.0 s timeout. Values from python3 -m chain.demo --slow-rate R
(seed=7, 1,000 refunds per point).
"""
import figlib as fl

rate = [0, 1, 2, 4, 8]
pilot = [0, 12, 23, 45, 86]
chain = [0, 0, 0, 0, 0]

fig, ax = fl.figure(4.5, 3.4)
ax.plot(rate, pilot, color=fl.C["fail"], linestyle="--", marker="s",
        lw=fl.STROKE["control"])
ax.plot(rate, chain, color=fl.C["verified"], linestyle="-", marker="o",
        lw=fl.STROKE["control"])
fl.label_line(ax, rate[-1], pilot[-1], "Pilot loop", color=fl.LABEL["fail"])
fl.label_line(ax, rate[-1], chain[-1] + 5, "Chain loop",
              color=fl.LABEL["verified"])
ax.annotate("Default run", xy=(2, 23), xytext=(2.4, 55),
            fontsize=9, arrowprops=dict(arrowstyle="-", lw=0.75,
                                        color=fl.GREY_DARK))
ax.set_xlabel("Calls answered after the timeout (%)")
ax.set_ylabel("Duplicate refunds per 1,000")
ax.set_xlim(0, 10.6)
ax.set_ylim(-3, 100)
ax.grid(axis="y")
fl.save(fig)
