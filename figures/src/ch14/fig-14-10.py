"""Figure 14.10  Self-hosting against the API, cost per task.

Reading order: left to right over monthly task volume (log scale).
The API costs the same per task at any volume; a fleet's fixed cost
spreads over more tasks as volume grows. Markers: April 2026 volume
and each fleet's break-even. From serving.tco and serving.bakeoff
(contract prices, 78% hit, 8.79 model calls a task, $3.20 a GPU-hour).
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "04-code" / "designlab"))
import figlib as fl  # noqa: E402
from serving.bakeoff import replay  # noqa: E402
from serving.tco import fleet  # noqa: E402
from serving.trace import day  # noqa: E402

r = replay(day(14), "stable-first")
api = r["bill"].usd("contract") / r["calls"] * 8.79
xs = [10_000 * 1.12 ** i for i in range(0, 64)]
fig, ax = fl.figure(4.5, 3.4)
ax.plot(xs, [api] * len(xs), color=fl.C["model"], lw=1.5, marker="")
fl.label_line(ax, 11_000, api * 1.25, f"API frontier, ${api:.3f}",
              color=fl.LABEL["model"], dx=0)
for i, (g, share, col, name) in enumerate(
        ((2, 0.5, "ops", "2 GPUs, 8B-class"),
         (16, 1.0, "fail", "16 GPUs, frontier-class"))):
    m = fleet(g, 3.20, sre_share=share).monthly
    ax.plot(xs, [m / x for x in xs], color=fl.C[col], lw=1.5,
            ls=fl.LINESTYLES[i + 1], marker="")
    be = m / api
    ax.plot([be], [api], marker="o", color=fl.C[col], ms=5)
    ax.vlines(be, 0.01, api, color=fl.C[col], lw=0.75, ls=":")
    ax.text(be * 0.93, 0.0125, f"{be / 1000:,.0f}k", fontsize=9.5,
            color=fl.LABEL[col], ha="right")
    fl.label_line(ax, 11_000, m / 11_000 * 1.25, name,
                  color=fl.LABEL[col], dx=0)
ax.axvline(20_100, color=fl.INK, lw=0.75, ls=":")
ax.text(21_500, 0.012, "April 2026", fontsize=9.5, color=fl.INK)
ax.set_xscale("log")
ax.set_yscale("log")
ax.set_xlim(10_000, 1_200_000)
ax.set_ylim(0.01, 20)
ax.set_xlabel("Tasks a month (log scale)")
ax.set_ylabel("Dollars per task (log scale)")
fl.save(fig)
