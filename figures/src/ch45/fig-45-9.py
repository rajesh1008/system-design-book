"""Figure 45.9  Privilege by design.

Reading order: one row per internal design, top to bottom in the
order the chapter walks them. The hatched coral bar is the number of
standing credentials the October request asked for; the label at its
end gives the design's answer: no standing credential, and how long
the run's own credential lives. From designs.privilege on the six
internal design files.
"""
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[2] / "04-code" / "designlab"))
import figlib as fl  # noqa: E402

from designs import internal  # noqa: E402
from designs.privilege import requested_vs_designed  # noqa: E402

LABEL = {"lakeshore-research": "Research", "lakeshore-coding": "Coding",
         "lakeshore-analytics": "Analytics", "lakeshore-itops": "IT ops",
         "lakeshore-compliance": "Compliance",
         "lakeshore-recon": "Reconciliation"}
specs = internal.load()
rows = [(LABEL[d], requested_vs_designed(specs[d]))
        for d in internal.ORDER][::-1]
fig, ax = fl.figure(4.5, 3.0)
for y, (name, r) in enumerate(rows):
    ax.barh(y, r["standing_asked"], color=fl.FILL["fail"],
            edgecolor=fl.C["fail"], hatch=fl.HATCH[1])
    fl.label_line(ax, r["standing_asked"], y,
                  f"now 0, "
                  f"{r['ttl']} min")
ax.set_yticks(range(len(rows)), [n for n, _ in rows])
ax.set_xlim(0, 7.5)
ax.set_xticks([0, 1, 2, 3])
ax.set_xlabel("Standing credentials asked in October")
ax.spines[["top", "right"]].set_visible(False)
fl.save(fig)
