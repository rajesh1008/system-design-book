"""Figure 21.9  Budget alarms by slot.

Reading order: one pair of bars per slot. Dark bars are the share of
17,385 replayed steps that raised an alarm in the shadow week of May 5
(instruction file v8, no compaction); light bars are the same steps on
the May 31 design. The v8 file broke its cap on every step, history
broke the budget on 14.8%, and retrieval was cut on 3.0%. On May 31 all
three are zero.
"""
import figlib as fl

slots = ["instructions\n(cap)", "history\n(budget)", "retrieved\n(cap)"]
shadow = [100.0, 14.8, 3.0]
after = [0, 0, 0]

fig, ax = fl.figure(4.5, 3.2)
x = range(len(slots))
ax.bar([i - 0.18 for i in x], shadow, width=0.34, color=fl.C["fail"],
       edgecolor=fl.C["fail"], label="May 5 shadow week")
ax.bar([i + 0.18 for i in x], after, width=0.34, color=fl.FILL["ops"],
       edgecolor=fl.C["ops"], hatch="///", label="May 31")
for i, v in enumerate(shadow):
    ax.text(i - 0.18, v + 2, f"{v:.1f}%", ha="center", fontsize=9,
            color=fl.INK)
    ax.text(i + 0.18, 2, "0", ha="center", fontsize=9, color=fl.LABEL["ops"])
ax.set_xticks(list(x), slots)
ax.set_ylabel("Steps with an alarm (%)")
ax.set_ylim(0, 112)
ax.legend(frameon=False, fontsize=9, loc="upper right")
ax.spines[["top", "right"]].set_visible(False)
fl.save(fig)
