"""Figure 24.9  The scoreboard falls and recovers.

Reading order: left panel, wrong-destination rebookings by day from
May 1 to June 14, 2026, all 38 on May 19, with DR-24.1 live on June 2;
right panel, the verified-outcome rate at the December, March, April,
and May checkpoints as the card recorded it, with May's rate checked
against the ticket marked below it (Lakeshore figures are
illustrative).
"""
from datetime import date, timedelta

import figlib as fl

d0 = date(2026, 5, 1)
days = [d0 + timedelta(days=i) for i in range(45)]
x = list(range(len(days)))
wrong = [38 if d == date(2026, 5, 19) else 0 for d in days]
fix = (date(2026, 6, 2) - d0).days
fig, (a1, a2) = fl.figure(4.5, 3.4, ncols=2,
                          gridspec_kw={"width_ratios": [1.5, 1],
                                       "wspace": 0.75})
a1.bar(x, wrong, width=1.6, color=fl.FILL["fail"],
       edgecolor=fl.C["fail"], lw=0.5)
a1.axvline(fix, color=fl.C["verified"], linestyle="--", lw=1)
a1.text(17.2, 37, "May 19: 38", fontsize=9.5, color=fl.LABEL["fail"],
        va="top", ha="right")
a1.text(fix + 0.8, 24, "fix live\nJun 2", fontsize=9.5,
        color=fl.LABEL["verified"])
a1.set_xticks([0, 18, fix, 44])
a1.set_xticklabels(["May 1", "May 19", "Jun 2", "Jun 14"])
a1.set_ylabel("Wrong-destination rebookings")
a1.set_ylim(0, 42)
pts = ["Dec", "Mar", "Apr", "May"]
vor = [97.9, 98.8, 98.1, 99.1]
a2.plot(pts, vor, color=fl.C["ops"], marker=fl.MARKERS[0],
        lw=fl.STROKE["emphasis"])
for p, v in zip(pts, vor):
    a2.annotate(f"{v}%", (p, v), xytext=(14 if p == "Dec" else 0, 9 if p != "Apr" else -16),
                textcoords="offset points", ha="center", fontsize=9,
                color=fl.LABEL["ops"])
a2.plot(["May"], [98.98], linestyle="none", marker="o",
        color=fl.C["fail"])
a2.annotate("98.98%\nvs ticket", ("May", 98.98), xytext=(-18, -30),
            textcoords="offset points", ha="center", fontsize=9,
            color=fl.LABEL["fail"])
a2.set_ylim(97.5, 99.5)
a2.set_xlim(-0.4, 3.4)
a2.set_ylabel("Verified-outcome rate (%)")
fl.save(fig)
