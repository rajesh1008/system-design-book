"""Figure 37.3  Uptime against verified outcomes.

Reading order: left to right, Wednesday, July 8, 2026, from the alias
move at 1:15 a.m. to the stop at 2:52 p.m. Cumulative front-door
availability and cumulative verified outcomes for the agent's tasks,
with the 99% verified target dashed. From reliability.july8
(Lakeshore figures are illustrative).
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "04-code" / "designlab"))
import figlib as fl  # noqa: E402
from datetime import timedelta  # noqa: E402

import matplotlib.dates as md  # noqa: E402
from reliability import july8  # noqa: E402

rec = july8.build()
ts = sorted(rec.tasks, key=lambda t: t.ended)
xs, up, ver = [], [], []
req = err = good = n = 0
t0 = july8.MOVED + timedelta(hours=3)
for t in ts:
    req += t.requests
    err += t.errors
    n += 1
    good += bool(t.verified)
    if t.ended >= t0:
        xs.append(t.ended)
        up.append(100 * (1 - err / req))
        ver.append(100 * good / n)
fig, ax = fl.figure(4.4, 3.2)
ax.plot(xs, up, color=fl.C["ops"], lw=1.5, marker="")
ax.plot(xs, ver, color=fl.C["fail"], lw=1.5, ls="--", marker="")
ax.axhline(99, color=fl.INK, lw=0.75, ls=":")
ax.text(xs[-1], up[-1] - 0.45, f"Uptime {up[-1]:.2f}%", ha="right",
        fontsize=9, color=fl.LABEL["ops"])
ax.text(xs[-1], ver[-1] - 0.5, f"Verified {ver[-1]:.1f}%", ha="right",
        va="top", fontsize=9, color=fl.LABEL["fail"])
ax.text(xs[0], 99.15, "Verified target 99%", fontsize=9, color=fl.INK)
ax.set_ylim(94, 100.6)
ax.set_ylabel("Cumulative since 1:15 a.m. (%)")
ax.xaxis.set_major_locator(md.HourLocator(byhour=range(2, 16, 3),
                                          tz=july8.MOVED.tzinfo))
ax.xaxis.set_major_formatter(md.DateFormatter("%-I %p", tz=july8.MOVED.tzinfo))
fl.save(fig)
