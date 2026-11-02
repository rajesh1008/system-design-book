"""Figure 10.3  Queuing at the provider, by hour of day.

Reading order: left to right across the day (Central time). The upper
line is the share of model calls that waited on the shared rate limit;
the lower line is the same calls replayed on the pilot's own limit.
From 04-code/designlab corpus.traces, seed 10.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "04-code" / "designlab"))
import figlib as fl  # noqa: E402
from corpus.traces import generate_traces  # noqa: E402

S = generate_traces(10)
hours = list(range(24))
shared, own = [], []
for h in hours:
    xs = [x for s in S if int(s.started[11:13]) == h for x in s.steps]
    shared.append(100 * sum(1 for x in xs if x.rejected_shared) / len(xs))
    own.append(100 * sum(1 for x in xs if x.rejected_own) / len(xs))
fig, ax = fl.figure(4.5, 3.4)
ax.plot(hours, shared, color=fl.C["fail"], lw=1.5, marker="o", ms=3)
ax.plot(hours, own, color=fl.C["ops"], lw=1.5, ls="--", marker="s", ms=3)
fl.label_line(ax, 18.5, shared[19] + 1.6, "shared account",
              color=fl.LABEL["fail"], dx=0)
fl.label_line(ax, 16, own[16] + 0.8, "own limit", color=fl.LABEL["ops"],
              dx=0)
peak = max(range(24), key=lambda h: shared[h])
fl.note(ax, (peak, shared[peak]), (12.5, shared[peak] + 0.6),
        "busy phone hours")
ax.set_xticks([0, 6, 12, 18, 23])
ax.set_xticklabels(["midnight", "6 a.m.", "noon", "6 p.m.", "11 p.m."])
ax.set_ylabel("Model calls that waited (%)")
ax.set_ylim(0, max(shared) * 1.3)
fl.save(fig)
