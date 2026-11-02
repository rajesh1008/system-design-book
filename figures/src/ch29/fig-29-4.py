"""Figure 29.4  Escape battery: build runner as found against sandbox.

Reading order: one pair of bars per probe class, the runner as found
above the sandbox per run. Values from sandbox.demo --part battery
(runner 37 of 40, sandbox 0 of 40); eight probes per class.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "04-code" / "designlab"))
import figlib as fl  # noqa: E402
from matplotlib.patches import Patch  # noqa: E402

classes = ("Filesystem", "Network", "Secrets", "Limits", "Persistence")
runner = (5, 8, 8, 8, 8)
sandbox = (0, 0, 0, 0, 0)
fig, ax = fl.figure(4.5, 3.0)
ys, yt = [], []
for i in range(len(classes)):
    base = (len(classes) - 1 - i) * 1.0
    ys += [base + 0.2, base - 0.2]
    yt.append(base)
vals = [v for pair in zip(runner, sandbox) for v in pair]
cols = [c for _ in classes for c in (fl.C["fail"], fl.FILL["verified"])]
edges = [c for _ in classes for c in (fl.C["fail"], fl.C["verified"])]
ax.barh(ys, vals, color=cols, edgecolor=edges, height=0.36)
ax.set_yticks(yt)
ax.set_yticklabels(classes)
for y, v in zip(ys, vals):
    fl.label_line(ax, max(v, 0.05), y, str(v))
ax.set_xlim(0, 10)
ax.legend(handles=[Patch(facecolor=fl.C["fail"], label="Runner as found"),
                   Patch(facecolor=fl.FILL["verified"],
                         edgecolor=fl.C["verified"],
                         label="Sandbox per run")],
          loc="lower center", bbox_to_anchor=(0.5, 1.0), ncol=2,
          fontsize=9, frameon=False)
ax.set_xlabel("Escapes of 8 (runner 37 of 40; sandbox 0 of 40)")
ax.grid(axis="x")
fl.save(fig)
