"""Figure 7.9  Duplicates against timeout rate, keyed and unkeyed.

Reading order: left to right along the timeout rate. Each point is one
replay of 10,000 runs (seed 2026, 04-code/designlab, effects.demo
sweep). The unkeyed line climbs with the rate; the keyed line stays
at zero.
"""
import figlib as fl

rates = [0, 1, 2, 5, 10]
unkeyed = [0, 68, 118, 328, 662]
keyed = [0, 0, 0, 0, 0]
fig, ax = fl.figure(4.5, 3.0)
ax.plot(rates, unkeyed, color=fl.C["fail"], marker=fl.MARKERS[0],
        linestyle=fl.LINESTYLES[0], lw=fl.STROKE["emphasis"])
ax.plot(rates, keyed, color=fl.C["verified"], marker=fl.MARKERS[1],
        linestyle=fl.LINESTYLES[1], lw=fl.STROKE["emphasis"])
fl.label_line(ax, 10, 662, "unkeyed, 662", color=fl.LABEL["fail"])
fl.label_line(ax, 10, 0, "keyed, 0", color=fl.LABEL["verified"])
ax.set_xlabel("Timeout rate (%)")
ax.set_ylabel("Duplicate effects")
ax.set_xlim(-0.3, 13.5)
ax.set_ylim(-30, 720)
ax.set_xticks(rates)
fl.save(fig)
