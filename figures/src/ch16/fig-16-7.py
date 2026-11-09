"""Figure 16.6  Repairs needed per call.

Reading order: left to right. Each bar is the rejected calls from May 18
to 31, 2026, that ended a given way: repaired after one try, repaired
after two, or handed to the agent desk. The share of all 807 rejected
calls is printed on each bar (Lakeshore figures are illustrative).
"""
import figlib as fl

labels = ["Repaired\nafter 1", "Repaired\nafter 2", "Handed\noff"]
counts = [702, 57, 48]
total = sum(counts)
toks = ["verified", "verified", "model"]

fig, ax = fl.figure(4.5, 3.0)
bars = ax.bar(labels, counts, width=0.6,
              color=[fl.FILL[t] for t in toks],
              edgecolor=[fl.C[t] for t in toks], linewidth=1.0)
bars[2].set_hatch("///")
for b, n in zip(bars, counts):
    ax.text(b.get_x() + b.get_width() / 2, n + 12,
            f"{n} ({100 * n / total:.0f}%)", ha="center", va="bottom",
            fontsize=9.5, color=fl.INK)
ax.set_ylabel("Rejected calls")
ax.set_ylim(0, 820)
ax.spines[["top", "right"]].set_visible(False)
fl.save(fig)
