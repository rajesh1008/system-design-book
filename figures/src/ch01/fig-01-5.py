"""Figure 1.5  Lakeshore's change volume by type, baseline year.

Reading order: one bar per change type, largest first; the dark part of
each bar is handled by people, the hatched part by self-service.
Fictional Lakeshore data; totals 2.1 million changes, 61% by people.
"""
import figlib as fl

types = ["Rebookings", "Cancellations", "Refunds", "Upgrades", "Other"]
total = [840, 520, 480, 150, 110]            # thousands
people_share = [0.70, 0.45, 0.66, 0.50, 0.60]
people = [t * s for t, s in zip(total, people_share)]
selfs = [t - p for t, p in zip(total, people)]

fig, ax = fl.figure(4.5, 3.2)
y = list(range(len(types)))[::-1]
ax.barh(y, people, color=fl.C["ops"], edgecolor=fl.C["ops"], height=0.6)
ax.barh(y, selfs, left=people, color=fl.FILL["org"], edgecolor=fl.C["org"],
        hatch="///", height=0.6)
ax.set_yticks(y)
ax.set_yticklabels(types)
for yi, t in zip(y, total):
    fl.label_line(ax, t, yi, f"{t:,}k")
ax.text(people[0] / 2, y[0], "People", ha="center", va="center",
        color="white", fontsize=9)
ax.text(people[0] + selfs[0] / 2, y[0], "Self", ha="center", va="center",
        color=fl.LABEL["org"], fontsize=9, backgroundcolor="white")
ax.set_xlabel("Changes per year (thousands)")
ax.set_xlim(0, 1000)
ax.grid(axis="x")
fl.save(fig)
