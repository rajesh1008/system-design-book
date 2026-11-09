"""Figure 44.4  Queue depth and approval latency.

Reading order: two panels sharing the time axis, 10 a.m. to 11 p.m.,
Thursday, September 10, 2026 (CDT). Top: cards waiting for a person,
peaking near 9,000 at 2:40 p.m. Bottom: the dashboard's approval
latency (median wait of cards decided in the last ten minutes) and
the age of the oldest card waiting, on a log scale; while the desk
worked newest first the dashboard read about 20 minutes and the
oldest card was more than three hours old. From golive.replay, the
as-run scenario (Lakeshore figures are illustrative).
"""
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[2] / "04-code" / "designlab"))
import figlib as fl  # noqa: E402
import matplotlib.pyplot as plt  # noqa: E402

from golive.replay import run, t  # noqa: E402

r = run("as-run")
lo, hi = t(10), r.scenario.tier2_release_at - 1
fig, (a1, a2) = plt.subplots(2, 1, figsize=(4.5, 3.8), sharex=True)
fl.figure  # theme applied on import
dx = [m / 60 for m, d in r.depth if lo <= m <= hi]
dy = [d for m, d in r.depth if lo <= m <= hi]
a1.plot(dx, dy, color=fl.C["ops"], lw=1.5, marker="")
a1.set_ylabel("Cards waiting", fontsize=9)
a1.annotate(f"{r.peak_depth:,} at 2:40 p.m.", (r.peak_at / 60,
            r.peak_depth), xytext=(15.6, 7600), fontsize=9,
            color=fl.INK, arrowprops=dict(arrowstyle="-", lw=0.6))
a1.axvline(r.scenario.surge_at / 60, color=fl.INK, lw=0.6, ls=":")
a1.text(r.scenario.surge_at / 60 + 0.15, 3600, "surge rule", fontsize=9,
        color=fl.INK)
lx = [m / 60 for m, v in r.latency if lo <= m <= hi and v > 0]
ly = [v for m, v in r.latency if lo <= m <= hi and v > 0]
ox = [m / 60 for m, v in r.oldest if lo <= m <= hi and v > 0]
oy = [v for m, v in r.oldest if lo <= m <= hi and v > 0]
a2.plot(ox, oy, color=fl.C["fail"], lw=1.5, ls="--", marker="", 
        label="Oldest card")
a2.plot(lx, ly, color=fl.C["verified"], lw=1.2, marker="o", ms=2.2,
        label="Dashboard latency")
a2.set_yscale("log")
a2.set_ylim(1, 2000)
a2.set_ylabel("Minutes (log)", fontsize=9)
a2.axvline(r.scenario.switch_at / 60, color=fl.INK, lw=0.6, ls=":")
a2.text(r.scenario.switch_at / 60 - 0.15, 1.5, "by departure",
        fontsize=9, ha="right", color=fl.INK)
a2.legend(fontsize=9, loc="lower right", frameon=False)
a2.set_xticks([10, 12, 14, 16, 18, 20, 22])
a2.set_xticklabels(["10", "noon", "2", "4", "6", "8", "10"],
                   fontsize=9)
fl.save(fig)
