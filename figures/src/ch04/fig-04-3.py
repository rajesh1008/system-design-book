"""Figure 4.3  Change mix by type, 12 types.

Reading order: one bar per change type, largest first; the solid part is
done by a person, the hatched part by self-service. Thousands of changes
in the 12 months to September 30, 2025. From baseline.volume.
"""
import figlib as fl

data = [("Rebook", 330, .62), ("Credit", 300, .40),
        ("Reprotect", 260, .85), ("Hotel cancel", 220, .52),
        ("Refund", 210, .61), ("Forced refund", 190, .74),
        ("Upgrade", 150, .50), ("Schedule", 130, .55),
        ("Hotel dates", 120, .75), ("Extras refund", 80, .62),
        ("Car", 60, .47), ("Name fix", 50, .76)]
fig, ax = fl.figure(4.1, 5.0)
y = list(range(len(data)))[::-1]
for yi, (name, t, s) in zip(y, data):
    ax.barh(yi, t * s, height=0.65, color=fl.C["ops"], edgecolor=fl.C["ops"])
    ax.barh(yi, t * (1 - s), left=t * s, height=0.65, color=fl.FILL["org"],
            edgecolor=fl.C["org"], hatch="///")
    fl.label_line(ax, t, yi, f"{t}k")
ax.set_yticks(y)
ax.set_yticklabels([d[0] for d in data])
ax.set_xlim(0, 400)
ax.set_xlabel("Changes (thousands)")
ax.grid(axis="x")
ax.text(330 * .62 / 2, y[0], "Person", ha="center", va="center",
        color="white", fontsize=9)
fl.save(fig)
