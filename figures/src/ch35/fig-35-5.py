"""Figure 35.5  Cost and tokens per span.

Reading order: left to right, the eight model-call spans of case
R-0002 in step order. Bars are the cost on each span; the line is the
input tokens, with the part the prefix cache served shaded. The second
call is the dearest because nothing is cached yet. From tracing.run.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "04-code" / "designlab"))
import figlib as fl  # noqa: E402
from harness.world import World, cases  # noqa: E402
from tracing import conventions as c  # noqa: E402
from tracing.run import Gateway, harness, live  # noqa: E402

case = next(x for x in cases(1000) if x.cid == "R-0002")
r = live(case, harness(), World(), Gateway())
chats = [s for s in r.trace if s.name.startswith("chat ")]
xs = list(range(1, len(chats) + 1))
cost = [1000 * float(s.attrs[c.COST]) for s in chats]
tin = [s.attrs[c.IN_TOKENS] / 1000 for s in chats]
cached = [s.attrs[c.CACHE_READ] / 1000 for s in chats]

fig, ax = fl.figure(4.5, 3.2)
ax.bar(xs, cost, color=fl.FILL["model"], edgecolor=fl.C["model"], lw=0.75,
       label="Cost on the span")
ax.set_xlabel("Step")
ax.set_ylabel("Cost (thousandths of a USD)")
ax.set_xticks(xs)
ax2 = ax.twinx()
ax2.plot(xs, tin, color=fl.C["ops"], marker="o", ms=4, lw=1.5,
         label="Input tokens")
ax2.fill_between(xs, 0, cached, facecolor=fl.FILL["ops"],
                 edgecolor=fl.C["ops"], hatch="//", lw=0.5,
                 label="Of which cached")
ax2.set_ylabel("Input tokens (thousands)")
ax2.set_ylim(0, 14)
ax.set_ylim(0, 14)
ax.set_zorder(ax2.get_zorder() + 1)
ax.patch.set_visible(False)
h1, l1 = ax.get_legend_handles_labels()
h2, l2 = ax2.get_legend_handles_labels()
ax.legend(h1 + h2, l1 + l2, loc="upper left", frameon=False, fontsize=9)
fl.save(fig)
