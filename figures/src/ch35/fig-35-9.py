"""Figure 35.9  Replay time distribution.

Reading order: left to right, seconds to replay one run, fetch from
the trace store plus compute, over 2,000 runs of Lakeshore's
benchmark. The dashed line is the median, the solid line the 2-second
target. Lakeshore figures are illustrative: tracing.replay.
production_times is a seeded model, and the lab measures only the
compute part, in milliseconds.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "04-code" / "designlab"))
import figlib as fl  # noqa: E402
from durable.bench import pct  # noqa: E402
from tracing.replay import production_times  # noqa: E402

xs = production_times()
med, p95 = pct(xs, 50), pct(xs, 95)
fig, ax = fl.figure(4.5, 3.2)
ax.hist(xs, bins=[1.2 + i * 0.025 for i in range(45)],
        color=fl.FILL["evidence"], edgecolor=fl.C["evidence"], lw=0.75)
ax.axvline(med, color=fl.INK, ls="--", lw=1.0)
fl.label_line(ax, med, 150, f"median {med:.1f} s", dx=-62)
ax.axvline(p95, color=fl.GREY_DARK, ls=":", lw=1.0)
ax.annotate(f"p95 {p95:.2f} s", xy=(p95, 110), xytext=(2.03, 125),
            fontsize=9, color=fl.INK,
            arrowprops=dict(arrowstyle="->", color=fl.GREY_DARK, lw=0.75))
ax.axvline(2.0, color=fl.C["fail"], lw=1.5)
fl.label_line(ax, 2.0, 60, "target 2 s", dx=3)
ax.set_xlim(1.2, 2.3)
ax.set_xlabel("Seconds to replay one run")
ax.set_ylabel("Runs")
fl.save(fig)
