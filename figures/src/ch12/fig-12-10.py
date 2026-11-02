"""Figure 12.10  The scoreboard falls and recovers.

Reading order: left panel, new duplicate refunds by day in April 2026,
all 212 on April 14, with the fix live on April 28; right panel, the
verified-outcome rate at the December, March, and April checkpoints
(Lakeshore figures are illustrative).
"""
import figlib as fl

days = list(range(1, 31))
dups = [212 if d == 14 else 0 for d in days]
fig, (a1, a2) = fl.figure(4.5, 3.4, ncols=2,
                          gridspec_kw={"width_ratios": [1.5, 1],
                                       "wspace": 0.75})
a1.bar(days, dups, width=0.8, color=fl.FILL["fail"],
       edgecolor=fl.C["fail"], lw=0.5)
a1.axvline(28, color=fl.C["verified"], linestyle="--", lw=1)
a1.text(14.8, 205, "Apr 14: 212", fontsize=9.5, color=fl.LABEL["fail"],
        va="top")
a1.text(27.3, 120, "fix live\nApr 28", fontsize=9.5, ha="right",
        color=fl.LABEL["verified"])
a1.set_xticks([1, 14, 28])
a1.set_xlabel("April 2026")
a1.set_ylabel("New duplicate refunds")
a1.set_ylim(0, 230)
pts = ["Dec", "Mar", "Apr"]
vor = [97.9, 98.8, 98.1]
a2.plot(pts, vor, color=fl.C["ops"], marker=fl.MARKERS[0],
        lw=fl.STROKE["emphasis"])
for p, v in zip(pts, vor):
    a2.annotate(f"{v}%", (p, v), xytext=(0, 9 if p == "Mar" else -16),
                textcoords="offset points", ha="center", fontsize=9.5,
                color=fl.LABEL["fail" if p == "Apr" else "ops"])
a2.set_ylim(97.5, 99.0)
a2.set_xlim(-0.4, 2.4)
a2.set_ylabel("Verified-outcome rate (%)")
fl.save(fig)
