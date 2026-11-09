"""Figure 4.5  Refund errors and disputes by month.

Reading order: left to right by month of refund. The solid bar is errors
found by October 14, 2025; the dashed outline is errors that will
eventually surface. The gap at the right is the dispute lag. Errors at
1:200 scale times 200. From baseline.errors.
"""
import figlib as fl

months = ["Oct", "Nov", "Dec", "Jan", "Feb", "Mar", "Apr", "May", "Jun",
          "Jul", "Aug", "Sep"]
found = [500, 600, 460, 440, 400, 440, 560, 320, 520, 460, 360, 40]
eventual = [500, 600, 460, 440, 400, 440, 560, 320, 520, 460, 580, 320]
fig, ax = fl.figure(4.5, 3.2)
x = range(12)
ax.bar(x, eventual, width=0.7, color="white", edgecolor=fl.C["fail"],
       ls="--", lw=1.2)
ax.bar(x, found, width=0.7, color=fl.C["ops"], edgecolor=fl.C["ops"])
ax.set_xticks(list(x))
ax.set_xticklabels(months, fontsize=9)
ax.set_ylabel("Refund errors")
ax.set_ylim(0, 800)
ax.grid(axis="y")
fl.note(ax, (11, 300), (6.2, 720), "Not yet disputed")
ax.text(0, 700, "Solid: found by Oct 14", fontsize=9)
ax.text(0, 625, "Dashed: eventual", fontsize=9)
fl.save(fig)
