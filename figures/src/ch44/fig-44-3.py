"""Figure 44.3  The storm day.

Reading order: left to right, Thursday, September 10, 2026, 9 a.m. to
midnight (CDT). Bars are changes arriving each fifteen minutes; the
shaded band is the closure of O'Hare, 11:00 a.m. to 5:00 p.m. Each
numbered marker is a decision from the incident record, listed under
the chart. From golive.day and golive.record (Lakeshore figures are
illustrative).
"""
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[2] / "04-code" / "designlab"))
import figlib as fl  # noqa: E402

from golive.day import CLOSE, REOPEN, generate  # noqa: E402
from golive.replay import run, t  # noqa: E402

r = run("as-run")
cs = generate()
bins = {}
for c in cs:
    b = int(c.t // 15) * 15
    bins[b] = bins.get(b, 0) + 1
xs = [b / 60 for b in sorted(bins) if t(9) <= b < 24 * 60]
ys = [bins[b] for b in sorted(bins) if t(9) <= b < 24 * 60]
fig, ax = fl.figure(4.3, 3.4)
ax.axvspan(CLOSE / 60, REOPEN / 60, color=fl.FILL["fail"], lw=0)
ax.bar(xs, ys, width=0.24, align="edge", color=fl.C["ops"], lw=0)
events = ((r.scenario.declare_at, "1"), (r.budget_spent_at, "2"),
          (r.scenario.emergency_at, "3"), (r.scenario.switch_at, "4"),
          (r.peak_at, "5"), (r.scenario.surge_at, "6"),
          (r.cleared_at, "7"))
top = max(ys) * 1.08
for i, (at, n) in enumerate(events):
    ax.axvline(at / 60, color=fl.INK, lw=0.6, ls=":")
    ax.text(at / 60, top * (1.0 if i % 2 else 0.88), n, ha="center",
            fontsize=9, color=fl.INK,
            bbox=dict(boxstyle="circle,pad=0.15", fc="white",
                      ec=fl.INK, lw=0.6))
ax.set_ylim(0, top * 1.2)
ax.set_xlim(9, 24)
ax.set_xticks([9, 12, 15, 18, 21, 24])
ax.set_xticklabels(["9", "noon", "3", "6", "9", "12"], fontsize=9)
ax.set_ylabel("Changes per 15 minutes")
ax.text(14, top * 1.11, "O'Hare closed", ha="center", fontsize=9,
        color=fl.LABEL["fail"], bbox=dict(fc=fl.FILL["fail"], ec="none",
                                          pad=1.5))
fl.save(fig)
