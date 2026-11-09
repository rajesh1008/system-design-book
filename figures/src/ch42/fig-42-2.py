"""Figure 42.5  Review outcomes over the year.

Reading order: stacked bars per month from November 2025 to September
2026, one bar segment per outcome: approved as submitted, changed,
declined. Fourteen reviews; June holds six. From review.log
(Lakeshore figures are illustrative).
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "04-code" / "designlab"))
import figlib as fl  # noqa: E402
from review.log import by_month, load_log  # noqa: E402

months = ["2025-11", "2025-12", "2026-01", "2026-02", "2026-03",
          "2026-04", "2026-05", "2026-06", "2026-07", "2026-08",
          "2026-09"]
names = ["Nov", "Dec", "Jan", "Feb", "Mar", "Apr", "May", "Jun",
         "Jul", "Aug", "Sep"]
m = by_month(load_log())
fig, ax = fl.figure(4.5, 3.0)
bottom = [0] * len(months)
series = (("approve", "Approved", "verified", 0),
          ("change", "Changed", "org", 1),
          ("decline", "Declined", "fail", 3))
for key, label, tok, h in series:
    vals = [m.get(k, {}).get(key, 0) for k in months]
    xs = [i for i, v in enumerate(vals) if v]
    ax.bar(xs, [vals[i] for i in xs], bottom=[bottom[i] for i in xs],
           width=0.62,
           color=fl.FILL[tok], edgecolor=fl.C[tok] if tok != "org"
           else fl.GREY_DARK, lw=0.9, hatch=fl.HATCH[h], label=label)
    bottom = [b + v for b, v in zip(bottom, vals)]
ax.set_xticks(range(len(months)))
ax.set_xticklabels(names, fontsize=9)
ax.tick_params(labelsize=9)
ax.set_ylabel("Designs reviewed")
ax.set_ylim(0, 7)
ax.legend(loc="upper left", fontsize=9, frameon=False)
fl.save(fig)
