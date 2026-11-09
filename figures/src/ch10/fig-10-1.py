"""Figure 10.2  Steps per task over 90 days.

Reading order: left to right. Bars are tasks by step count; the line
is the fitted lognormal; markers sit at the median and the p95. From
04-code/designlab (corpus.traces, capacity.estimate), seed 10.
"""
import math
import sys
from collections import Counter
from pathlib import Path
from statistics import NormalDist

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "04-code" / "designlab"))
import figlib as fl  # noqa: E402
from corpus.traces import generate_traces  # noqa: E402
from capacity.estimate import fit_traces  # noqa: E402

S = generate_traces(10)
f = fit_traces(S)
n = Counter(len(s.steps) for s in S if s.is_task)
xs = list(range(2, 31))
fig, ax = fl.figure(4.5, 3.4)
ax.bar(xs, [n[x] for x in xs], color=fl.FILL["evidence"],
       edgecolor=fl.C["evidence"], lw=0.75, width=0.8)
mu, sg = math.log(f.steps_median), f.steps_sigma
d = NormalDist(mu, sg)
fit = [f.tasks * (d.cdf(math.log(x + 0.5)) - d.cdf(math.log(x - 0.5)))
       for x in xs]
ax.plot(xs, fit, color=fl.C["model"], lw=1.5, ls="--")
fl.label_line(ax, 16.5, fit[11] + 120, "lognormal fit", color=fl.LABEL["model"])
for x, t in ((f.steps_median, "median 7.4"), (f.steps_p95, "p95 19")):
    ax.axvline(x, color=fl.INK, lw=0.75, ls=":")
    ax.text(x + 0.4, max(n.values()) * 0.95, t, fontsize=9.5,
            color=fl.INK)
fl.note(ax, (24, n[24] + 5), (22, 520), "a long right tail")
ax.set_xlabel("Steps per task")
ax.set_ylabel("Tasks")
fl.save(fig)
