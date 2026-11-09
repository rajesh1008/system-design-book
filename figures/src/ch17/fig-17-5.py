"""Figure 17.5  Cost per classification step.

Reading order: left to right. The first bar is the frontier model on
the full 1,200-token prompt. The next two are the distilled student at
the May pilot volume and the June volume, stacked from serving cost,
escalations back to the frontier, and upkeep (relabeling and golden-set
runs) spread over the month's steps. Values from adapt.cost.
"""
import figlib as fl

labels = ["Frontier", "Student,\nMay pilot", "Student,\nJune"]
serve = [0, 0.02, 0.02]
esc = [5.04, 0.35, 0.35]
keep = [0, 0.29, 0.05]
tot = [5.04, 0.66, 0.42]

fig, ax = fl.figure(4.5, 3.0)
x = range(3)
ax.bar(x, esc, width=0.6, color=[fl.FILL["model"]] * 3,
       edgecolor=fl.C["model"], label="Frontier calls")
ax.bar(x, serve, bottom=esc, width=0.6, color=fl.FILL["ops"],
       edgecolor=fl.C["ops"], label="Serving")
b = ax.bar(x, keep, bottom=[e + s for e, s in zip(esc, serve)],
           width=0.6, color=fl.FILL["evidence"],
           edgecolor=fl.C["evidence"], label="Upkeep")
for p in b:
    p.set_hatch("///")
for i, t in enumerate(tot):
    ax.text(i, t + 0.08, f"${t / 1000:.5f}", ha="center", va="bottom",
            fontsize=9, color=fl.INK)
ax.set_xticks(list(x))
ax.set_xticklabels(labels)
ax.set_ylabel("USD per step (thousandths)")
ax.set_ylim(0, 5.8)
ax.legend(loc="upper right", fontsize=9, frameon=False)
ax.spines[["top", "right"]].set_visible(False)
fl.save(fig)
