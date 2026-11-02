"""Figure 14.5  Prefix cache hit before and after the re-layout.

Reading order: left to right, three groups (the provider API and the
two engines), two bars each: the pilot's layout and stable-first. The
same 300 recorded tasks, seed 14. From serving.bakeoff.replay.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "04-code" / "designlab"))
import figlib as fl  # noqa: E402
from serving.bakeoff import replay  # noqa: E402
from serving.trace import day  # noqa: E402

tasks = day(14)
caches = (("api", "Provider API"), ("engine-a", "Engine A"),
          ("engine-b", "Engine B"))
fig, ax = fl.figure(4.5, 3.2)
for j, (lay, col, hatch, name) in enumerate(
        (("pilot", "fail", "///", "pilot layout"),
         ("stable-first", "verified", "", "stable first"))):
    for i, (c, _) in enumerate(caches):
        h = 100 * replay(tasks, lay, c)["hit"]
        x = i + (j - 0.5) * 0.38
        ax.bar(x, h, width=0.36, color=fl.FILL[col], edgecolor=fl.C[col],
               lw=0.75, hatch=hatch)
        ax.text(x, h + 1.5, f"{h:.0f}%", ha="center", fontsize=9.5,
                color=fl.INK)
    fl.label_line(ax, -0.45 + 1.55 * j, 92 if j else 22, name,
                  color=fl.LABEL[col], dx=0)
ax.set_xticks(range(3))
ax.set_xticklabels([n for _, n in caches])
ax.set_ylim(0, 100)
ax.set_ylabel("Input tokens read from cache (%)")
fl.save(fig)
