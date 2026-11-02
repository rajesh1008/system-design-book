"""Figure 19.4  Recall by method on the golden set.

Reading order: top to bottom, one pair of bars per configuration, each
adding one stage to the one above it. The upper bar of each pair is the
lab's 350-question golden set; the lower is Lakeshore's golden set of
May 2026 (Lakeshore figures are illustrative). The reranker is the
stage that moves recall most in both.
"""
import figlib as fl

configs = ["Lexical only", "Dense only", "Hybrid", "Hybrid + dates",
           "Hybrid + dates\n+ rerank"]
lab = [63.7, 79.7, 81.1, 81.4, 97.4]
lake = [64, 71, 81, 85, 89]

fig, ax = fl.figure(4.5, 3.6)
ys = list(range(len(configs)))[::-1]
h = 0.36
ax.barh([y + h / 2 for y in ys], lab, height=h, color=fl.FILL["knowledge"],
        edgecolor=fl.C["knowledge"], linewidth=1.0)
ax.barh([y - h / 2 for y in ys], lake, height=h, color=fl.FILL["verified"],
        edgecolor=fl.C["verified"], linewidth=1.0, hatch="///")
for y, a, b in zip(ys, lab, lake):
    ax.text(a + 1, y + h / 2, f"{a:.1f}%", va="center", fontsize=9.5,
            color=fl.LABEL["knowledge"])
    ax.text(b + 1, y - h / 2, f"{b}%", va="center", fontsize=9.5,
            color=fl.LABEL["verified"])
ax.set_yticks(ys)
ax.set_yticklabels(configs, fontsize=9.5)
ax.set_xlim(0, 112)
ax.set_xticks([0, 25, 50, 75, 100])
ax.set_xlabel("Recall at 10 (%)")
ax.text(0, len(configs) - 0.35, "Lab (upper bar)", fontsize=9.5,
        color=fl.LABEL["knowledge"], va="bottom")
ax.text(48, len(configs) - 0.35, "Lakeshore (lower, hatched)", fontsize=9.5,
        color=fl.LABEL["verified"], va="bottom")
ax.set_ylim(-0.6, len(configs) + 0.1)
ax.spines[["top", "right"]].set_visible(False)
fl.save(fig)
