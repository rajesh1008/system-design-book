"""Figure 4.4  Cost per change decomposed.

Reading order: two stacked bars, person and self-service, each split into
its cost pools; the dashed line is the blended cost per change. USD per
change, 12 months to September 30, 2025. From baseline.cost.
"""
import figlib as fl

person = [("Handle labor", 31.50), ("Repeat contacts", 8.40),
          ("Supervision", 5.60), ("Seats", 4.80), ("Rework", 4.60)]
selfs = [("Platform", 3.10), ("Fees", 2.90), ("Payments", 1.60),
         ("Abandons", 1.90), ("Rework", 1.90)]
toks = ["ops", "org", "evidence", "knowledge", "fail"]
fig, ax = fl.figure(4.5, 4.4)
for x, parts in ((0, person), (1, selfs)):
    base = 0
    for j, (name, v) in enumerate(parts):
        tok = toks[j]
        ax.bar(x, v, bottom=base, width=0.55, color=fl.FILL[tok],
               edgecolor=fl.C[tok], hatch=fl.HATCH[j])
        if x == 0:
            ax.text(0.33, base + v / 2, f"{name} ${v:.2f}", va="center",
                    fontsize=9)
        base += v
    fl.label_line(ax, x, base, f"${base:.2f}", dx=-14, dy=8)
ax.axhline(37.94, color=fl.INK, ls="--", lw=1)
ax.text(1.35, 39.2, "Blended $37.94", ha="right", fontsize=9)
ax.set_xticks([0, 1])
ax.set_xticklabels(["Person, 61%", "Self-service, 39%"])
ax.set_xlim(-0.45, 1.45)
ax.set_ylim(0, 62)
ax.set_ylabel("USD per change")
ax.grid(axis="y")
fl.save(fig)
