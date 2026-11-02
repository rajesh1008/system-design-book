"""Figure 15.7  Where the open-weights model runs.

Reading order: one row per question, top to bottom; columns are the
four places the same open-weights model can run, and the name under
each question is who answers it. Lakeshore's choice, the managed
endpoint in its own cloud account, is emphasized (illustrative).
"""
import sys
from pathlib import Path

from matplotlib.patches import Rectangle

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "04-code" / "designlab"))
import figlib as fl  # noqa: E402

heads = ("Provider\nAPI", "Third-\nparty host", "Managed\nendpoint", "Self-\nhosting")
rows = (("Data residence", "Owen Fletcher",
         ("Provider's\nregion", "Host's\nregion", "Lakeshore\naccount", "Lakeshore\naccount")),
        ("Change control", "Dr. Hannah Clarke",
         ("Pinned\nalias", "Host may\nswap", "File-hash\npin", "File-hash\npin")),
        ("License", "Owen Fletcher",
         ("Provider\nterms", "Model and\nhost terms", "Model\nlicense", "Model\nlicense")),
        ("Supply continuity", "Daniel Price",
         ("Provider\nretires", "Host\nretires", "Weights\nkept", "Weights\nkept")),
        ("Who owns the work", "Ben Carter",
         ("Provider", "Shared", "Lakeshore,\nmostly", "Lakeshore")))
x0, w = 1.45, 0.78
fig, ax = fl.figure(4.5, 3.6)
n = len(rows)
ax.set_xlim(0, x0 + 4 * w)
ax.set_ylim(-0.1, n + 1.0)
ax.axis("off")
for j, h in enumerate(heads):
    ax.text(x0 + j * w + w / 2, n + 0.5, h, ha="center", va="center", fontsize=9,
            fontweight="bold", color=fl.INK)
ax.add_patch(Rectangle((x0 + 2 * w + 0.02, 0.02), w - 0.04, n + 0.96, facecolor="none",
                       edgecolor=fl.INK, lw=2.5))
for i, (q, who, cells) in enumerate(rows):
    y = n - 1 - i
    ax.add_patch(Rectangle((0.0, y + 0.06), x0 + 4 * w, 0.88, facecolor=fl.FILL["evidence"],
                           edgecolor=fl.C["evidence"], lw=0.5))
    ax.text(0.04, y + 0.62, q, va="center", fontsize=9, fontweight="bold", color=fl.INK)
    ax.text(0.04, y + 0.3, who, va="center", fontsize=9, style="italic", color=fl.INK)
    for j, c in enumerate(cells):
        ax.text(x0 + j * w + w / 2, y + 0.5, c, ha="center", va="center", fontsize=9,
                color=fl.INK)
fl.save(fig)
