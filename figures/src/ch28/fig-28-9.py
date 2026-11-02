"""Figure 28.9  The dashboard that was always green.

Reading order: left to right, hours from Friday, June 12, 00:00 to
Wednesday, June 17, 00:00 CDT. The upper line is the checks the
actor claimed each hour; the lower line is the allowed reads the
gateway trail shows. The band at the top is the dashboard, green
throughout. Values from loops.demo --part opening and the June 15
fix at 10:00 a.m. (hour 82). Lakeshore figures are illustrative.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "04-code" / "designlab"))
import figlib as fl  # noqa: E402

hours = list(range(0, 120))
claimed = [1840 for _ in hours]
reads = [0 if h < 82 else 1840 for h in hours]
fig, ax = fl.figure(4.5, 3.3)
ax.plot(hours, reads, color=fl.C["fail"], ls=fl.LINESTYLES[0],
        lw=3.0, label="Allowed reads, trail", zorder=2)
ax.plot(hours, claimed, color=fl.C["model"], ls=fl.LINESTYLES[1],
        lw=1.25, label="Claimed checks", zorder=3)
ax.axhspan(2050, 2200, color=fl.FILL["verified"])
ax.text(2, 2125, "Dashboard: green", va="center", fontsize=9,
        color=fl.INK)
ax.axvline(82, color=fl.GREY_LIGHT, lw=0.75)
fl.label_line(ax, 83, 900, "Fix, June 15")
ax.set_xlim(0, 120)
ax.set_ylim(-100, 2250)
ax.set_xticks([0, 24, 48, 72, 96, 120])
ax.set_xticklabels(["Jun 12", "13", "14", "15", "16", "17"])
ax.set_ylabel("Watches per hour")
ax.legend(loc="center left", frameon=False, fontsize=9)
fl.save(fig)
