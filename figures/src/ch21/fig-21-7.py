"""Figure 21.7  Success by run length before and after compaction.

Reading order: left to right in run length, 2,000 replayed runs at seed
21. The top line is the May 31 design (isolation plus pinned
compaction), flat at about 97% to 98%. The middle line is no compaction,
which falls to 90.7% on runs of 17 to 24 steps. The bottom line is the
free-form summary shadowed on May 12, which is worse than doing nothing
on long runs.
"""
import figlib as fl

b = ["1-4", "5-8", "9-12", "13-16", "17-24"]
after = [98.1, 97.1, 96.4, 96.2, 98.3]
none = [98.1, 97.1, 95.5, 95.3, 90.7]
summ = [98.1, 97.1, 93.3, 92.0, 83.7]

fig, ax = fl.figure(4.5, 3.2)
x = range(len(b))
ax.plot(x, after, color=fl.C["verified"], marker="s", lw=1.8)
ax.plot(x, none, color=fl.C["fail"], marker="o", ls="--", lw=1.4)
ax.plot(x, summ, color=fl.C["fail"], marker="^", ls=":", lw=1.4)
fl.label_line(ax, 4, 98.3, "May 31 design", color=fl.LABEL["verified"],
              dy=4)
fl.label_line(ax, 4, 90.7, "no compaction", color=fl.LABEL["fail"])
fl.label_line(ax, 4, 83.7, "free summary", color=fl.LABEL["fail"])
ax.set_xticks(list(x), b)
ax.set_xlim(-0.2, 5.4)
ax.set_xlabel("Run length (steps)")
ax.set_ylabel("Task success (%)")
ax.set_ylim(80, 100)
ax.spines[["top", "right"]].set_visible(False)
fl.save(fig)
