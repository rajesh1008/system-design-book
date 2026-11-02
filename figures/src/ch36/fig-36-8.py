"""Figure 36.8  The scoreboard falls and recovers.

Reading order: left panel, refund proposals to a destination that did
not pay, by day from June 1 to July 10, 2026, one on June 24, with
destination-v1 active on June 26 and the finding closed on July 3;
right panel, the verified-outcome rate at the December, March, April,
May, and June checkpoints, which rose while the finding was open
(Lakeshore figures are illustrative).
"""
from datetime import date, timedelta

import figlib as fl

d0 = date(2026, 6, 1)
days = [d0 + timedelta(days=i) for i in range(40)]
x = list(range(len(days)))
bad = [1 if d == date(2026, 6, 24) else 0 for d in days]
fix = (date(2026, 6, 26) - d0).days
closed = (date(2026, 7, 3) - d0).days
fig, (a1, a2) = fl.figure(4.5, 3.4, ncols=2,
                          gridspec_kw={"width_ratios": [1.1, 1.3],
                                       "wspace": 0.6})
a1.bar(x, bad, width=1.2, color=fl.FILL["fail"],
       edgecolor=fl.C["fail"], lw=0.5)
a1.axvline(fix, color=fl.C["verified"], linestyle="--", lw=1)
a1.axvline(closed, color=fl.GREY_DARK, linestyle=":", lw=1)
a1.text(22.4, 1.12, "Jun 24: 1", fontsize=9.5, color=fl.LABEL["fail"],
        ha="right")
a1.text(fix - 0.8, 0.62, "policy\nJun 26", ha="right", fontsize=9.5,
        color=fl.LABEL["verified"])
a1.text(closed + 0.8, 0.3, "closed\nJul 3", fontsize=9.5, color=fl.INK)
a1.set_xticks([0, 23, 39])
a1.set_xticklabels(["Jun 1", "Jun 24", "Jul 10"])
a1.set_yticks([0, 1])
a1.set_ylabel("Proposals to a card\nthat did not pay")
a1.set_ylim(0, 1.3)
pts = ["D", "M", "A", "M ", "J"]
vor = [97.9, 98.8, 98.1, 99.1, 99.3]
a2.plot(pts, vor, color=fl.C["ops"], marker=fl.MARKERS[0],
        lw=fl.STROKE["emphasis"])
for p, v in zip(pts, vor):
    a2.annotate(f"{v}%", (p, v), xytext=(16 if p == "D" else (-12 if p == "J" else 0),
                                         9 if p not in ("A", "D") else -16),
                textcoords="offset points", ha="center", fontsize=9,
                color=fl.LABEL["ops"])
a2.set_ylim(97.5, 99.7)
a2.set_xlim(-0.4, 4.4)
a2.set_ylabel("Verified-outcome rate (%)")
a2.set_xlabel("Dec to Jun checkpoints")
fl.save(fig)
