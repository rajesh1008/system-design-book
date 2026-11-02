"""Figure 17.6  Train, validation, and the held-out month.

Reading order: left to right in time. Each bar is one month of change
messages from adapt.data at seed 17. December to March train the
student, April validates the threshold, and May is held out as the
golden set of 1,200 cases. The hatched part of each bar is messages in
app shorthand, which the training months never contain.
"""
import figlib as fl

months = ["Dec", "Jan", "Feb", "Mar", "Apr", "May"]
total = [807, 815, 800, 815, 802, 1571]
short = [0, 0, 0, 0, 88, 277]
role = ["model"] * 4 + ["ops", "evidence"]
names = {"model": "Train", "ops": "Validate", "evidence": "Held out"}

fig, ax = fl.figure(4.5, 3.3)
plain = [t - s for t, s in zip(total, short)]
ax.bar(months, plain, width=0.62, color=[fl.FILL[r] for r in role],
       edgecolor=[fl.C[r] for r in role], linewidth=1.0)
b2 = ax.bar(months, short, bottom=plain, width=0.62,
            color=[fl.FILL[r] for r in role],
            edgecolor=[fl.C[r] for r in role], linewidth=1.0)
for b in b2:
    b.set_hatch("///")
for i, (t, r) in enumerate(zip(total, role)):
    ax.text(i, t + 25, f"{t:,}", ha="center", va="bottom", fontsize=9,
            color=fl.INK)
for x, r in ((1.5, "model"), (4, "ops"), (5, "evidence")):
    ax.text(x, 1880, names[r], ha="center", fontsize=9.5,
            color=fl.LABEL[r], fontweight="bold")
ax.text(4.55, 1180, "hatched:\nshorthand", ha="right", fontsize=9,
        color=fl.INK)
ax.set_ylabel("Messages")
ax.set_ylim(0, 2000)
ax.spines[["top", "right"]].set_visible(False)
fl.save(fig)
