"""Figure 8.6  Approval queue age with and without backpressure.

Reading order: left to right in minutes after the fan-out. The oldest
card on the desk, sampled every 5 minutes. Without a cap the oldest
card ages with the backlog; with 50 pending it stays near 11 minutes.
Values from python3 -m spine.demo --part desk (seed 8, 400 approvals,
6 reviewers, 80 s a card).
"""
import figlib as fl

mins = list(range(0, 90, 5))
nocap = [0.0, 5.0, 9.9, 14.8, 19.8, 24.7, 29.7, 34.6, 39.6, 44.5, 49.5,
         54.4, 59.4, 64.3, 69.2, 74.2, 79.1, 84.1]
cap = [0.0, 5.0, 9.9, 11.2, 11.0, 10.8, 10.8, 11.2, 11.0, 11.3, 10.8,
       10.8, 11.4, 11.5, 10.8, 11.0, 11.0, 11.4]

fig, ax = fl.figure(4.5, 3.4)
ax.plot(mins, nocap, color=fl.C["fail"], marker=fl.MARKERS[1],
        ls=fl.LINESTYLES[1], ms=4)
ax.plot(mins, cap, color=fl.C["verified"], marker=fl.MARKERS[0],
        ls=fl.LINESTYLES[0], ms=4)
ax.axhline(15, color=fl.GREY_DARK, lw=0.75, ls=":")
ax.text(1, 16.5, "quote expires, 15 min", fontsize=9, color=fl.INK)
fl.label_line(ax, 52, 60, "no cap", color=fl.LABEL["fail"])
fl.label_line(ax, 60, 4.5, "cap 50 pending", color=fl.LABEL["verified"])
ax.set_xlabel("Minutes after the fan-out")
ax.set_ylabel("Oldest card on the desk (min)")
ax.set_xlim(0, 90)
ax.set_ylim(0, 90)
fl.save(fig)
