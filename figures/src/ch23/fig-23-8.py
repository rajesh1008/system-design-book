"""Figure 23.8  What the siblings own.

Reading order: one row per input concern, top to bottom: what this
chapter decides at the edge, and which sibling volume owns the
concern at depth.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "04-code" / "designlab"))
import figlib as fl  # noqa: E402
from matplotlib.patches import Rectangle  # noqa: E402

rows = (("Document parsing\nand OCR", "Contract fields,\nconfidence, route", "Document AI\nvolume"),
        ("Speech recognition\nand synthesis", "Turn budget,\nread-back", "Voice agents\nvolume"),
        ("Injection attacks\nand red teaming", "Tag at the edge,\nno free text", "Security\nvolume"),
        ("Retrieval over\ndocuments", "Admitted fields\nonly", "Retrieval\nvolume"),
        ("Personal data\nin scans", "What is kept,\nfor how long", "Privacy\nvolume"))
cols = (0.0, 1.6, 3.15)
heads = ("Concern", "Decided here", "Owned at depth")
fig, ax = fl.figure(4.5, 3.6)
n = len(rows)
ax.set_xlim(0, 4.6)
ax.set_ylim(-0.1, n + 0.9)
ax.axis("off")
for x, h in zip(cols, heads):
    ax.text(x + 0.05, n + 0.45, h, va="center", fontsize=10,
            fontweight="bold", color=fl.INK)
for i, r in enumerate(rows):
    y = n - 1 - i
    ax.add_patch(Rectangle((0.0, y + 0.06), 4.6, 0.88,
                           facecolor=fl.FILL["org"], edgecolor=fl.C["org"],
                           lw=0.75))
    for x, t in zip(cols, r):
        ax.text(x + 0.05, y + 0.5, t, va="center", fontsize=9,
                color=fl.INK, fontweight="bold" if x == cols[1] else None)
fl.save(fig)
