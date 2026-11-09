"""Figure 44.5  The scoreboard falls and recovers (the board page).

Reading order: four panels, left to right and top to bottom, as the
board page of Thursday, October 22, 2026 lays them out. Top left: the
agent's share of changes by month, December 2025 to September 2026,
with the four falls marked in red (April 14, May 19, June 24, and
September 10). Top right: the blended cost of a change against the
$37.94 baseline and the $10 target. Bottom left: verified outcomes by
day, September 7 to 20, falling to 98.7% on the storm day and back
over the card's 99.5% line on September 13. Bottom right: baseline
against year end. From golive.pilot, golive.ramp, and golive.review
(Lakeshore figures are illustrative).
"""
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[2] / "04-code" / "designlab"))
import figlib as fl  # noqa: E402
import matplotlib.pyplot as plt  # noqa: E402

from golive.ramp import MONTHS, agent_share  # noqa: E402
from golive.review import GATE, daily_verified, recovered_on  # noqa: E402

fig, axs = plt.subplots(2, 2, figsize=(4.5, 4.2))
(a, b), (c, d) = axs
fl.figure  # theme is applied on import

# Top left: agent share by month, falls in red.
xs = list(range(len(MONTHS)))
falls = {"Apr 2026", "May 2026", "Jun 2026", "Sep 2026"}
a.bar(xs, [agent_share(m) * 100 for m in MONTHS], width=0.7,
      color=[fl.C["fail"] if m in falls else fl.FILL["ops"]
             for m in MONTHS],
      edgecolor=[fl.C["fail"] if m in falls else fl.C["ops"]
                 for m in MONTHS],
      hatch=None, lw=0.75)
a.set_xticks(xs)
a.set_xticklabels([m[0] for m in MONTHS], fontsize=9)
a.set_ylabel("Agent %", fontsize=9)
a.set_ylim(0, 50)

# Top right: blended cost per change.
cost = (("D", 36.50), ("M", 31.95), ("A", 32.25), ("M", 29.34),
        ("J", 24.01), ("A", 13.20), ("S", 9.76))
b.plot(range(len(cost)), [v for _, v in cost], color=fl.C["ops"],
       lw=1.5, marker="o", ms=3)
b.axhline(10, color=fl.C["verified"], lw=0.9, ls="--")
b.text(0, 11.5, "$10", fontsize=9, color=fl.LABEL["verified"])
b.set_xticks(range(len(cost)))
b.set_xticklabels([k for k, _ in cost], fontsize=9)
b.set_ylabel("Blended $", fontsize=9)
b.set_ylim(0, 40)

# Bottom left: verified by day around the storm.
s = daily_verified()
c.axhline(GATE * 100, color=fl.INK, lw=0.75, ls="--")
c.plot([x for x, _ in s], [v * 100 for _, v in s],
       color=fl.C["verified"], lw=1.5, marker="o", ms=2.5)
c.plot([10], [s[3][1] * 100], marker="o", ms=5, color=fl.C["fail"])
c.text(10.6, 98.72, "98.7%", fontsize=9, color=fl.LABEL["fail"])
back = recovered_on(s)
c.text(back + 0.4, 99.2, f"back {back}th", fontsize=9,
       color=fl.LABEL["verified"])
c.set_xticks([7, 10, 13, 16, 19])
c.set_xticklabels(["7", "10", "13", "16", "19"], fontsize=9)
c.set_xlabel("September", fontsize=9)
c.set_ylabel("Verified %", fontsize=9)
c.set_ylim(98.5, 99.8)

# Bottom right: baseline against year end.
d.axis("off")
rows = (("People", "61%", "9%"), ("Refund error", "0.8%", "0.3%"),
        ("Per year", "$80M", "$20.5M"))
d.text(0.55, 0.92, "Base", fontsize=9, fontweight="bold", color=fl.INK)
d.text(0.82, 0.92, "Sep", fontsize=9, fontweight="bold", color=fl.INK)
for i, (k, v0, v1) in enumerate(rows):
    y = 0.68 - i * 0.26
    d.text(0.0, y, k, fontsize=9, color=fl.INK)
    d.text(0.55, y, v0, fontsize=9, color=fl.INK)
    d.text(0.82, y, v1, fontsize=9, color=fl.LABEL["verified"],
           fontweight="bold")
fig.tight_layout(pad=0.4)
fl.save(fig)
