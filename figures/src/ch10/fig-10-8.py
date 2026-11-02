"""Figure 10.8  Monday surge arrivals.

Reading order: left to right across the day (Central time). Mondays
and other weekdays, each the mean of 90 days of pilot sessions scaled
to the ceiling of 4.34 million contacts a year; the dotted line is the
mean hour. From 04-code/designlab corpus.traces, seed 10.
"""
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "04-code" / "designlab"))
import figlib as fl  # noqa: E402
from corpus.traces import generate_traces  # noqa: E402

S = generate_traces(10)
k = (4_340_000 / 8760) / (len(S) / (90 * 24))
mon, wk = [0] * 24, [0] * 24
days = {"mon": set(), "wk": set()}
for s in S:
    t = datetime.fromisoformat(s.started)
    if t.weekday() == 0:
        mon[t.hour] += 1
        days["mon"].add(t.date())
    elif t.weekday() < 5:
        wk[t.hour] += 1
        days["wk"].add(t.date())
mon = [k * v / len(days["mon"]) for v in mon]
wk = [k * v / len(days["wk"]) for v in wk]
h = list(range(24))
fig, ax = fl.figure(4.5, 3.4)
ax.step(h, mon, where="post", color=fl.C["fail"], lw=1.5, marker="")
ax.step(h, wk, where="post", color=fl.C["ops"], lw=1.5, ls="--", marker="")
ax.axhline(4_340_000 / 8760, color=fl.INK, lw=0.75, ls=":")
fl.label_line(ax, 14.5, mon[14] + 110, "Mondays", color=fl.LABEL["fail"],
              dx=0)
fl.label_line(ax, 11.5, wk[12] - 170, "Tuesday to Friday",
              color=fl.LABEL["ops"], dx=0)
ax.text(0.3, 4_340_000 / 8760 + 40, "mean hour", fontsize=9.5,
        color=fl.INK)
fl.note(ax, (9, mon[8]), (12, mon[8] + 60), "8 to 10 a.m., 2.6x")
ax.set_xticks([0, 6, 12, 18, 23])
ax.set_xticklabels(["midnight", "6 a.m.", "noon", "6 p.m.", "11 p.m."])
ax.set_ylabel("Sessions an hour at the ceiling")
ax.set_ylim(0, max(mon) * 1.18)
fl.save(fig)
