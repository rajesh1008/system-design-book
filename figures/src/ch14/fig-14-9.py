"""Figure 14.9  The engines compared, as of November 2026.

Reading order: one row per engine or orchestration layer, top to
bottom. Columns: how prefixes are reused, whether prefill and decode
can be split, and the release current when this was checked. Sources:
each project's documentation and release pages, accessed November 2,
2026 (listed in 06-research/source-list.md).
"""
import sys
from pathlib import Path

from matplotlib.patches import Rectangle

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "04-code" / "designlab"))
import figlib as fl  # noqa: E402

rows = (("vLLM", "Hashed blocks,\nLRU eviction", "Experimental", "v0.32.0"),
        ("SGLang", "Radix tree\nover tokens", "Yes", "v0.5.22"),
        ("TensorRT-LLM", "Block reuse,\npriority LRU", "Yes", "v1.2.1"),
        ("Dynamo", "Routes by\nKV location", "Yes", "v1.6.1"),
        ("llm-d", "Prefix-aware\nrouting", "Yes", "v1.0"))
cols = (0.0, 1.25, 2.55, 3.65)
heads = ("Engine", "Prefix reuse", "Split P/D", "Release")
fig, ax = fl.figure(4.5, 3.6)
n = len(rows)
ax.set_xlim(0, 4.6)
ax.set_ylim(-0.2, n + 0.9)
ax.axis("off")
for x, h in zip(cols, heads):
    ax.text(x + 0.05, n + 0.45, h, va="center", fontsize=10,
            fontweight="bold", color=fl.INK)
for i, row in enumerate(rows):
    y = n - 1 - i
    tok = "model" if i < 3 else "ops"
    ax.add_patch(Rectangle((0.0, y + 0.06), 1.2, 0.88,
                           facecolor=fl.FILL[tok], edgecolor=fl.C[tok],
                           lw=0.75))
    ax.text(0.06, y + 0.5, row[0], va="center", fontsize=9.5,
            color=fl.TEXT_ON[tok])
    for x, t in zip(cols[1:], row[1:]):
        ax.text(x + 0.05, y + 0.5, t, va="center", fontsize=9.5,
                color=fl.INK)
    ax.plot([0, 4.6], [y, y], color="#D9DCE1", lw=0.75, ls="-", marker="")
fl.save(fig)
