"""Figure 11.8  Cost of isolation by level.

Reading order: one row per level, start time on a log scale. Circles are
cold starts; squares are starts from a warm pool. The two lowest levels
were measured by the chapter's lab (median of 15 starts); the rest are
Lakeshore's March 2026 bench (illustrative). The dotted line is the
p95 task latency of 47 seconds, for scale.
"""
import figlib as fl

rows = [("Own process", 11.1, None),
        ("OS sandbox", 17.1, None),
        ("Container", 410, 60),
        ("MicroVM", 780, 35),
        ("Own VM", 21000, 900)]

fig, ax = fl.figure(4.5, 3.2)
ys = list(range(len(rows)))[::-1]
for y, (name, cold, warm) in zip(ys, rows):
    ax.plot([cold], [y], marker=fl.MARKERS[0], color=fl.C["ops"], ms=7,
            ls="none")
    ax.text(cold * 1.25, y + 0.18, f"{cold:,.0f} ms" if cold >= 100
            else f"{cold:.1f} ms", fontsize=9, va="bottom")
    if warm:
        ax.plot([warm], [y], marker=fl.MARKERS[1], color=fl.C["org"],
                ms=6, ls="none", mfc="white")
        ax.plot([warm, cold], [y, y], color=fl.GREY_LIGHT, lw=0.8,
                zorder=0)
ax.axvline(47000, color=fl.GREY_DARK, ls=":", lw=0.9)
ax.text(40000, len(rows) - 0.55, "p95 task", ha="right", fontsize=9)
ax.set_xscale("log")
ax.set_xlim(5, 90000)
ax.set_ylim(-0.7, len(rows) - 0.3)
ax.set_yticks(ys)
ax.set_yticklabels([r[0] for r in rows])
ax.set_xlabel("Start time per session (ms, log scale)")
ax.plot([], [], marker=fl.MARKERS[0], color=fl.C["ops"], ls="none",
        label="cold")
ax.plot([], [], marker=fl.MARKERS[1], color=fl.C["org"], mfc="white",
        ls="none", label="warm pool")
ax.legend(loc="center right", frameon=False, fontsize=9)
fl.save(fig)
