"""Figure 21.6  Success against context length.

Reading order: left to right in context length. One fixed task set from
the context.rot harness at seed 21, replayed at thirteen lengths. Success
holds near 96% to 60,000 tokens, then falls with no error raised. The
vertical lines mark the knee at 60,000 and the budget at 48,000, set
below it.
"""
import figlib as fl

k = [10, 20, 30, 40, 50, 60, 70, 80, 90, 100, 110, 120, 130]
s = [96.5, 95.5, 96.0, 96.5, 95.2, 95.5, 94.2, 91.5, 91.0, 89.8, 88.0,
     87.3, 87.3]

fig, ax = fl.figure(4.5, 3.2)
ax.plot(k, s, color=fl.C["model"], marker="o", ms=4, lw=1.6)
ax.axvline(60, color=fl.C["fail"], ls="--", lw=1.1)
ax.axvline(48, color=fl.C["ops"], ls=":", lw=1.3)
ax.text(61.5, 97.4, "knee\n60,000", fontsize=9, color=fl.LABEL["fail"],
        va="top")
ax.text(46.5, 88.0, "budget\n48,000", fontsize=9, color=fl.LABEL["ops"],
        ha="right")
ax.set_xlabel("Context at the step (thousand tokens)")
ax.set_ylabel("Task success (%)")
ax.set_ylim(85, 98)
ax.spines[["top", "right"]].set_visible(False)
fl.save(fig)
