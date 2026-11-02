"""Figure 18.8  Forecast against actual bill.

Reading order: left to right by month. The shaded band is the driver
forecast written on June 1, 2026; points are the scoreboard's actual
cost per verified outcome. From cost.demo --part forecast.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "04-code" / "designlab"))
import figlib as fl  # noqa: E402
from cost.forecast import ACTUAL, forecast  # noqa: E402

rows = forecast()
names = ["Mar", "Apr", "May", "Jun", "Jul", "Aug"]
act = [ACTUAL[m] for m in ("March 2026", "April 2026", "May 2026",
                           "June 2026", "July 2026")]
fig, ax = fl.figure(4.5, 3.0)
xs = [3, 4, 5]
ax.fill_between(xs, [r["low"] for r in rows], [r["high"] for r in rows],
                color=fl.FILL["ops"], edgecolor=fl.C["ops"], lw=0.75)
ax.plot(xs, [r["mid"] for r in rows], color=fl.C["ops"], lw=1.25,
        ls="--")
ax.plot(range(5), act, color=fl.C["org"], marker="o", lw=1.25)
for x, v in enumerate(act):
    ax.text(x, v + 0.07, f"${v:.2f}", ha="center", fontsize=9.5,
            color=fl.INK)
ax.text(4.1, 1.47, "June 1 forecast", fontsize=9.5,
        color=fl.LABEL["ops"], ha="center")
ax.set_xticks(range(6))
ax.set_xticklabels(names)
ax.set_ylim(1.3, 3.25)
ax.set_ylabel("Dollars per verified outcome")
fl.save(fig)
