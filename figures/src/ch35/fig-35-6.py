"""Figure 35.6  Cost per decision distribution.

Reading order: left to right, cost per decision in USD over 1,000 lab
runs, one histogram per kind of decision. The dashed line is the p95
on a normal day; the solid line is the alert at $0.12. With the
prefix cache off the p95 moves past the alert. From tracing.cost.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "04-code" / "designlab"))
import figlib as fl  # noqa: E402
from tracing import cost  # noqa: E402
from tracing.run import fleet  # noqa: E402

normal = fleet(1000)
off = cost.distribution(fleet(1000, cache=False).results)["all"]["p95"]
by = {}
for r in normal.results:
    for d in cost.decisions(r.trace, r.evidence):
        by.setdefault(d["kind"], []).append(float(d["usd"]))
p95 = cost.distribution(normal.results)["all"]["p95"]

fig, ax = fl.figure(4.5, 3.2)
bins = [i * 0.005 for i in range(0, 46)]
for i, (k, tok) in enumerate((("refund", "policy"), ("decline", "ops"),
                              ("handoff", "fail"))):
    ax.hist(by[k], bins=bins, color=fl.FILL[tok], edgecolor=fl.C[tok],
            lw=0.75, hatch=fl.HATCH[i], label=f"{k.replace('handoff', 'hand-off')} ({len(by[k])})")
ax.axvline(p95, color=fl.INK, ls="--", lw=1.0)
fl.label_line(ax, p95, 118, f"p95 ${p95:.3f}", dx=3)
ax.axvline(0.12, color=fl.C["fail"], lw=1.5)
fl.label_line(ax, 0.12, 100, "alert $0.12", dx=3)
ax.axvline(off, color=fl.C["fail"], ls=":", lw=1.25)
fl.label_line(ax, off, 120, f"cache off\np95 ${off:.2f}", dx=-48)
ax.set_xlim(0, 0.23)
ax.set_xlabel("Cost per decision (USD)")
ax.set_ylabel("Decisions")
ax.legend(loc="upper left", bbox_to_anchor=(0.54, 0.72), frameon=False,
          fontsize=9)
fl.save(fig)
