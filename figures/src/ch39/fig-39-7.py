"""Figure 39.7  Releases and rollbacks, July 13 to August 31.

Reading order: left to right, one week per group, weeks starting on
Monday; the solid bar is releases in the log, the hatched bar is what
June's rule (a code deploy) would have counted, and a marked count
above a week is a rollback. From release.log (Lakeshore figures are
illustrative).
"""
import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "04-code" / "designlab"))
import figlib as fl  # noqa: E402
from release import log as L  # noqa: E402

start = date(2026, 7, 13)
weeks = [0] * 7
june = [0] * 7
back = [0] * 7
for e in L.LOG:
    w = (date.fromisoformat("2026-" + e.date) - start).days // 7
    weeks[w] += 1
    june[w] += bool(e.june)
    back[w] += e.result == "rolled_back"
labels = ["Jul 13", "Jul 20", "Jul 27", "Aug 3", "Aug 10", "Aug 17",
          "Aug 24"]
fig, ax = fl.figure(4.5, 3.0)
xs = range(len(weeks))
ax.bar([x - 0.2 for x in xs], weeks, width=0.38, color=fl.FILL["ops"],
       edgecolor=fl.C["ops"], lw=0.9, label="Releases in the log")
ax.bar([x + 0.2 for x in xs], june, width=0.38, color="white",
       edgecolor=fl.C["ops"], lw=0.9, hatch="///",
       label="Counted by June's rule")
for x, n in zip(xs, back):
    if n:
        ax.plot(x - 0.2, weeks[x] + 0.5, marker="X", ms=8,
                color=fl.C["fail"], ls="")
        ax.text(x - 0.2, weeks[x] + 0.9, f"{n} rolled back", ha="center",
                fontsize=9, color=fl.LABEL["fail"])
ax.set_xticks(list(xs))
ax.set_xticklabels(labels, fontsize=9)
ax.set_ylim(0, max(weeks) + 2)
ax.set_ylabel("Releases per week")
ax.legend(fontsize=9, frameon=False, loc="upper left")
fl.save(fig)
