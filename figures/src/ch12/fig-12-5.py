"""Figure 12.5  Forty minutes on April 14, 2026.

Reading order: top panel, the share of processor calls in the slow
band; bottom panel, duplicate credits paid each minute on the batch
path. The dashed line marks the alert at 3:52 p.m. CDT. From the
fall-1 corpus (seed 2026) and failure.batch.replay_injected.
"""
import sys
from collections import Counter
from pathlib import Path

import figlib as fl

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "04-code" / "designlab"))
from corpus.fall1 import generate_fall1, hms, slow_share  # noqa: E402
from failure.batch import replay_injected  # noqa: E402
from failure.reconcile import extra_credits  # noqa: E402

run = replay_injected(generate_fall1(2026))
per_min = Counter(int(x["at"] // 60) for x in extra_credits(run.lines()))
m0, m1 = hms(14, 55) // 60, hms(16, 5) // 60
mins = list(range(m0, m1 + 1))
x = [(m - m0) for m in mins]
fig, (a1, a2) = fl.figure(4.5, 3.6, nrows=2, sharex=True,
                          gridspec_kw={"height_ratios": [1, 1.6]})
a1.plot(x, [100 * slow_share(m * 60 + 30) for m in mins],
        color=fl.C["ops"], lw=fl.STROKE["emphasis"])
a1.set_ylabel("Slow calls (%)")
a1.set_ylim(0, 80)
a2.bar(x, [per_min.get(m, 0) for m in mins], width=0.85,
       color=fl.FILL["fail"], edgecolor=fl.C["fail"], lw=0.5)
a2.set_ylabel("Duplicates a minute")
alert = hms(15, 52) // 60 - m0
for a in (a1, a2):
    a.axvline(alert, color=fl.C["fail"], linestyle="--", lw=1)
fl.label_line(a1, alert, 70, "alert 3:52 p.m.", color=fl.LABEL["fail"],
              dx=3)
ticks = [hms(h, m) // 60 - m0 for h, m in ((15, 0), (15, 20), (15, 40),
                                             (16, 0))]
a2.set_xticks(ticks)
a2.set_xticklabels(["3:00", "3:20", "3:40", "4:00"])
a2.set_xlabel("April 14, 2026, p.m. CDT")
a2.set_ylim(0, 17)
a2.text(0.02, 0.97, "212 duplicates, $61,000", transform=a2.transAxes,
        fontsize=9.5, color=fl.LABEL["fail"], va="top")
fl.save(fig)
