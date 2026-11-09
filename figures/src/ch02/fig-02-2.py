"""Figure 2.3  What the dashboard showed against what the log showed.

Reading order: two lanes on one time axis (seconds after 14:32:07 CT).
Top lane is the vendor dashboard, one bar. Bottom lane is the framework
log, the first attempt, the timeout mark, and the retry. Credits from
the settlement file are marked with triangles under the axis lanes.
"""
import figlib as fl

fig, ax = fl.figure(4.5, 3.2)
ax.barh(2, 8.1, left=0, height=0.5, color=fl.FILL["ops"],
        edgecolor=fl.C["ops"])
ax.text(4.05, 2, "One call, 200", ha="center", va="center",
        color=fl.LABEL["ops"], fontsize=9)
ax.barh(1, 8.0, left=0, height=0.5, color=fl.FILL["fail"],
        edgecolor=fl.C["fail"], hatch="///")
ax.text(4.0, 1, "Attempt one", ha="center", va="center",
        color=fl.LABEL["fail"], fontsize=9, backgroundcolor="white")
ax.barh(1, 0.9, left=9.0, height=0.5, color=fl.FILL["ops"],
        edgecolor=fl.C["ops"])
ax.text(10.05, 1, "Retry", ha="left", va="center", fontsize=9)
ax.plot([7, 10], [0, 0], linestyle="none", marker="^", markersize=9,
        color=fl.C["fail"])
ax.text(7, -0.25, "Credit", ha="center", va="top", fontsize=9)
ax.text(10, -0.25, "Credit", ha="center", va="top", fontsize=9)
ax.set_yticks([2, 1, 0])
ax.set_yticklabels(["Dashboard", "Framework log", "Settlement"])
ax.set_xlabel("Seconds after the first call")
ax.set_xlim(-0.3, 12)
ax.set_ylim(-0.75, 2.5)
ax.grid(axis="x")
fl.save(fig)
