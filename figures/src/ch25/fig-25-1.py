"""Figure 25.1  Change log: harness changes against model changes.

Reading order: one bar per week from January 1 to May 31, 2026. The
stacked bars are harness changes, split by whether they went through a
release; the dots are model changes. Lakeshore figures are illustrative.
"""
import figlib as fl
import numpy as np

weeks = ["Jan 1", "Jan 5", "Jan 12", "Jan 19", "Jan 26", "Feb 2", "Feb 9",
         "Feb 16", "Feb 23", "Mar 2", "Mar 9", "Mar 16", "Mar 23", "Mar 30",
         "Apr 6", "Apr 13", "Apr 20", "Apr 27", "May 4", "May 11", "May 18",
         "May 25"]
released = [1, 3, 3, 4, 3, 3, 4, 4, 3, 4, 3, 4, 4, 3, 6, 5, 3, 4, 3, 5, 3, 1]
unreleased = [0, 1, 1, 2, 1, 1, 2, 2, 1, 2, 2, 2, 3, 2, 3, 2, 2, 2, 3, 2, 2, 3]
model = {14: 2, 17: 1, 19: 4, 21: 1}
assert sum(released) + sum(unreleased) == 117 and sum(unreleased) == 41
assert sum(model.values()) == 8

x = np.arange(len(weeks))
fig, ax = fl.figure(5.4, 3.6)
ax.bar(x, released, color=fl.FILL["ops"], edgecolor=fl.C["ops"], lw=0.6,
       label="Harness, through a release")
ax.bar(x, unreleased, bottom=released, color="white", edgecolor=fl.C["ops"],
       hatch="///", lw=0.6, label="Harness, no release")
mx = list(model)
ax.scatter(mx, [model[k] for k in mx], color=fl.C["model"], zorder=3, s=22,
           marker="D", label="Model changes")
ax.set_xticks(x[::3])
ax.set_xticklabels(weeks[::3])
ax.set_ylabel("Changes in the week")
ax.legend(loc="upper left", frameon=False, fontsize=9.5)
fl.save(fig)
