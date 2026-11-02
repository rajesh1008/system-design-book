"""Figure 24.5  May 19, 2026: 38 passengers.

Reading order: left to right, Tuesday 11 a.m. to Wednesday 5 p.m.
CDT. Three running counts of the 38 travelers rebooked to Denver: when
each rebooking was made (11:31 a.m. to 12:18 p.m.), when the desk
reached each one, and when each was in Phoenix. The dashed line marks
detection at 2:47 p.m. From corpus.fall2, seed 2026 (Lakeshore figures
are illustrative).
"""
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "04-code" / "designlab"))
import figlib as fl  # noqa: E402
from corpus.fall2 import generate_fall2  # noqa: E402

t = generate_fall2(2026)
t0 = datetime.fromisoformat("2026-05-19T11:00:00-05:00")


def h(s):
    return (datetime.fromisoformat(s) - t0).total_seconds() / 3600


wrong = sorted(h(r["at"]) for r in t["fall2_runs"]
               if r["proposal_dest"] == "DEN" and r["disposition"] == "rebooked")
rec = t["fall2_recovery"]
series = (("rebooked to Denver", wrong, "fail", 0),
          ("reached by the desk", sorted(h(r["contacted_at"]) for r in rec),
           "ops", 1),
          ("in Phoenix", sorted(h(r["arrived_phx"]) for r in rec),
           "verified", 2))
fig, ax = fl.figure(4.5, 3.2)
end = 30.0
for lab, xs, tok, i in series:
    xx = [0.0] + xs + [end]
    yy = [0] + list(range(1, len(xs) + 1)) + [len(xs)]
    ax.step(xx, yy, where="post", color=fl.C[tok], marker="",
            lw=fl.STROKE["emphasis"] if tok == "fail" else 1.4,
            linestyle=("-", "--", "-.")[i], label=lab)
det = h("2026-05-19T14:47:00-05:00")
ax.axvline(det, color=fl.C["ops"], linestyle=":", lw=1)
fl.label_line(ax, det, 20, "found 2:47 p.m.", color=fl.LABEL["ops"], dx=3)
ax.set_xlim(0, end)
ax.set_ylim(0, 42)
ax.set_xticks([0, 6, 13, 22, 29])
ax.set_xticklabels(["11 a.m.", "5 p.m.", "Wed", "9 a.m.", "4 p.m."])
ax.set_xlabel("May 19 to 20, 2026, CDT")
ax.set_ylabel("Travelers (of 38)")
ax.legend(loc="lower right", fontsize=9, frameon=False)
fl.save(fig)
