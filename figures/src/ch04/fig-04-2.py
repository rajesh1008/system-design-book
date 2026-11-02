"""Figure 4.2  Contacts and changes: the funnel from 14 million to 2.1 million.

Reading order: top to bottom, each bar a subset of the one above.
Values from python3 -m baseline.demo (corpus ops-v1, seed 2026).
"""
import figlib as fl

steps = ["All contacts", "About a change", "Distinct changes",
         "Done by a person"]
vals = [14.00, 4.34, 2.10, 1.281]
fig, ax = fl.figure(4.3, 3.3)
y = list(range(len(steps)))[::-1]
for i, (yi, v) in enumerate(zip(y, vals)):
    tok = "org" if i < 2 else "ops"
    ax.barh(yi, v, height=0.6, color=fl.FILL[tok] if i < 2 else fl.C[tok],
            edgecolor=fl.C[tok], hatch="///" if i < 2 else "")
    fl.label_line(ax, v, yi, f"{v:.2f}M")
ax.set_yticks(y)
ax.set_yticklabels(steps)
ax.set_xlim(0, 17)
ax.set_xlabel("Baseline year (millions)")
ax.grid(axis="x")
fl.note(ax, (1.2, y[2] + 0.3), (7.5, y[2] + 0.75), "15% of contacts")
fl.save(fig)
