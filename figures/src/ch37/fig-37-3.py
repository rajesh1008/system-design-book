"""Figure 37.2  Error budget burn on verified outcomes.

Reading order: left to right, June 28 to August 31, 2026. The share of
the rebooking slice's 28-day budget spent, as run and as replayed with
the classifier pinned; dashed lines at half spent (sign-off) and
spent (freeze). From reliability.daily (Lakeshore figures are
illustrative).
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "04-code" / "designlab"))
import figlib as fl  # noqa: E402
from datetime import date  # noqa: E402

import matplotlib.dates as md  # noqa: E402
from reliability import daily  # noqa: E402

fig, ax = fl.figure(4.4, 3.2)
for pinned, tok, ls, lab in ((False, "ops", "-", "As run"),
                             (True, "verified", "--", "Pinned replay")):
    r = [x for x in daily.rolling(daily.series(pinned=pinned))
         if x[0] >= date(2026, 6, 28)]
    ys = [100 * x[4] for x in r]
    ax.plot([x[0] for x in r], ys, color=fl.C[tok], ls=ls, lw=1.5, marker="")
    at = date(2026, 7, 22) if not pinned else date(2026, 8, 12)
    y = dict((x[0], 100 * x[4]) for x in r)[at]
    ax.text(at, y + (6 if not pinned else -11), lab, fontsize=9,
            color=fl.LABEL[tok])
for y, lab in ((50, "Half spent: sign-off"), (100, "Spent: freeze")):
    ax.axhline(y, color=fl.C["fail"], lw=0.75, ls=":")
    ax.text(date(2026, 6, 29), y + 2.5, lab, fontsize=9, color=fl.INK)
ax.annotate("July 8", xy=(date(2026, 7, 8), 87), xytext=(date(2026, 7, 12), 92),
            fontsize=9, color=fl.INK,
            arrowprops=dict(arrowstyle="-", color=fl.INK, lw=0.75))
ax.set_ylim(0, 115)
ax.set_ylabel("Budget spent, 28 days (%)")
ax.xaxis.set_major_locator(md.MonthLocator())
ax.xaxis.set_major_formatter(md.DateFormatter("%b 1"))
fl.save(fig)
