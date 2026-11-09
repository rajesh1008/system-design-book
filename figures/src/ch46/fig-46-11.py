"""Figure 46.11  Scored answers by level.

Reading order: left to right by level. Each level's bar is the grey
step. Green circles are the twelve worked answers, every one at or
above its bar; red squares are the other twelve, every one below its
level, two of them above the bar and still below the level because a
required item is missing. From ladder.rubric over the 24 notes.
"""
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[2] / "04-code" / "designlab"))
import figlib as fl  # noqa: E402

from ladder import notes, rubric  # noqa: E402
from ladder.levels import LEVELS  # noqa: E402

codes = [lv.code for lv in LEVELS]
fig, ax = fl.figure(4.5, 3.0)
for i, lv in enumerate(LEVELS):
    ax.hlines(lv.bar, i - 0.4, i + 0.4, colors=fl.GREY_DARK, lw=1.5)
seen = {}
for aid, n in sorted(notes.load_all().items()):
    s = rubric.score(n)
    x = codes.index(s.level)
    k = (x, aid.endswith("a"))
    off = 0.12 * seen.get(k, 0) - 0.06
    seen[k] = seen.get(k, 0) + 1
    if aid.endswith("a"):
        ax.plot(x - 0.15 + off, s.total, "o", color=fl.C["verified"],
                ms=6)
    else:
        ax.plot(x + 0.15 + off, s.total, "s", color=fl.C["fail"], ms=5)
ax.set_xticks(range(len(codes)), codes)
ax.set_ylim(0, 15)
ax.set_ylabel("Rubric total, of 14")
ax.text(-0.4, 14.6, "Worked, clear", color=fl.LABEL["verified"],
        fontsize=9)
ax.text(3.4, 1.0, "Other, below", color=fl.LABEL["fail"], fontsize=9)
fl.save(fig)
