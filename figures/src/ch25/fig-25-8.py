"""Figure 25.8  Success by harness version.

Reading order: left to right, three periods of refund conversations. The
middle bar is the same build string with the May 27 settings edit, the
harness nobody had versioned. Lower is better. Lakeshore figures are
illustrative.
"""
import figlib as fl

labels = ["Build as\nreleased", "Same build,\nMay 28", "Harness\n1.0.0"]
vals = [1.2, 3.9, 1.1]
toks = ["ops", "fail", "verified"]

fig, ax = fl.figure(4.5, 3.2)
for i, (v, t) in enumerate(zip(vals, toks)):
    ax.bar(i, v, color=fl.FILL[t], edgecolor=fl.C[t], lw=1.0, width=0.6,
           hatch="///" if t == "fail" else "")
    ax.text(i, v + 0.1, f"{v:.1f}%", ha="center", va="bottom", fontsize=9.5,
            color=fl.LABEL[t], fontweight="bold")
ax.set_xticks(range(3))
ax.set_xticklabels(labels, fontsize=10)
ax.set_ylabel("Refund conversations handed off")
ax.set_ylim(0, 4.8)
fl.save(fig)
