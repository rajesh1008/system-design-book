"""Figure 40.6  Platform economics: shared against duplicated.

Reading order: monthly cost against the number of use cases. Each use
case that builds its own control plane carries about 1.4 engineers of
gateway, identity, policy, evaluation, trace, and on-call work; the
shared plane carries a fixed team and a small cost per use case. The
lines cross at about 2.7 use cases. From agentplatform.economics
(Lakeshore figures are illustrative).
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "04-code" / "designlab"))
import figlib as fl  # noqa: E402
from agentplatform import economics as ec  # noqa: E402

ns = list(range(1, 11))
fig, ax = fl.figure(4.5, 3.2)
dup = [ec.duplicated(n) / 1000 for n in ns]
sh = [ec.shared(n) / 1000 for n in ns]
ax.plot(ns, dup, color=fl.C["ops"], lw=1.5)
ax.plot(ns, sh, color=fl.C["org"], lw=1.5, ls="--")
fl.label_line(ax, 10, dup[-1], "One per use case", fl.LABEL["ops"],
              dx=-80, dy=8)
fl.label_line(ax, 10, sh[-1], "Shared", fl.LABEL["org"], dx=-36, dy=-9)
be = ec.break_even()
ax.axvline(be, color=fl.GREY_DARK, lw=0.6, ls=":")
fl.note(ax, (be, ec.shared(3) / 1000), (4.2, 25),
        f"Break-even, {be:.1f}")
ax.plot([3], [ec.shared(3) / 1000], "o", color=fl.C["org"], ms=4)
ax.set_xlim(1, 10.3)
ax.set_ylim(0, 240)
ax.set_xlabel("Use cases")
ax.set_ylabel("Thousand dollars a month")
fl.save(fig)
