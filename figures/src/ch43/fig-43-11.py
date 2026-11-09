"""Figure 43.11  Cost per verified outcome across six designs.

Reading order: one bar per design, cheapest at the top: the agent
path's cost per verified outcome, with the person path's cost and the
payback in months as direct labels. Design-time estimates from each
design's stated inputs, priced at Lakeshore's contract rates and Chapter
4's loaded minute; not measurements. From designs.economics.month.
"""
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[2] / "04-code" / "designlab"))
import figlib as fl  # noqa: E402

from designs import DESIGNS  # noqa: E402
from designs.economics import month  # noqa: E402

LABEL = {"telecom-care": "Telecom", "lakeshore-rebooking": "Rebooking",
         "lakeshore-refunds": "Refunds", "bank-payments": "Bank",
         "insurer-claims": "Claims", "lender-collections": "Collections"}
ms = sorted((month(DESIGNS[d]) for d in list(DESIGNS)[:6]),
            key=lambda m: m.per_outcome, reverse=True)
fig, ax = fl.figure(4.5, 3.2)
ys = range(len(ms))
for y, m in zip(ys, ms):
    lake = m.design.startswith("lakeshore")
    ax.barh(y, m.per_outcome, color=fl.FILL["ops"],
            edgecolor=fl.C["ops"], hatch=fl.HATCH[1] if lake else "")
    fl.label_line(ax, m.per_outcome, y,
                  f"\\${m.per_outcome:.2f} vs \\${m.person_cost:.2f},"
                  f" {m.payback_months:.1f} mo")
ax.set_yticks(list(ys), [LABEL[m.design] for m in ms])
ax.set_xlim(0, 22)
ax.set_xlabel("USD per verified outcome")
ax.spines[["top", "right"]].set_visible(False)
fl.save(fig)
