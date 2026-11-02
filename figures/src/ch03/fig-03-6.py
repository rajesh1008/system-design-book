"""Figure 3.6  Inference engines by deployment shape.

Reading order: two bands, bottom to top. The engines run a model on a
node; the cluster layers sit above the engines and route between them.
Versions read from release pages on 2026-11-02.
"""
import figlib as fl
from matplotlib.patches import Rectangle

fig, ax = fl.figure(4.5, 3.0)
ax.set_xlim(0, 10)
ax.set_ylim(0, 6.6)
ax.axis("off")
engines = [("vLLM", "0.32"), ("SGLang", "0.5"), ("TensorRT-LLM", "1.2")]
layers = [("NVIDIA Dynamo", "1.6", "any of the three"),
          ("llm-d", "1.0", "Kubernetes, vLLM or SGLang")]
ax.text(0.1, 2.85, "Engine: one model on a node", fontweight="bold")
for k, (name, ver) in enumerate(engines):
    x = 0.1 + k * 3.3
    ax.add_patch(Rectangle((x, 0.5), 3.0, 1.9, facecolor=fl.C["model"],
                           edgecolor=fl.C["model"], lw=fl.STROKE["data"]))
    ax.text(x + 1.5, 1.7, name, ha="center", va="center", color=fl.TEXT_ON["model"])
    ax.text(x + 1.5, 1.05, ver, ha="center", va="center", color=fl.TEXT_ON["model"],
            **fl.mono(ver))
ax.text(0.1, 6.2, "Cluster layer: routing, caching, scaling", fontweight="bold")
for k, (name, ver, over) in enumerate(layers):
    x = 0.1 + k * 5.0
    ax.add_patch(Rectangle((x, 3.5), 4.7, 2.3, facecolor=fl.FILL["ops"],
                           edgecolor=fl.C["ops"], lw=fl.STROKE["control"]))
    ax.text(x + 2.35, 5.05, f"{name} {ver}", ha="center", va="center",
            color=fl.LABEL["ops"])
    ax.text(x + 2.35, 4.2, over, ha="center", va="center", fontsize=9.5,
            fontstyle="italic", color=fl.LABEL["ops"])
fl.save(fig)
