"""Shared table drawing for the ch47 table-figures (not a figure)."""
import figlib as fl
from matplotlib.patches import Rectangle


def table(rows, heads, cols, width=5.0, toks=None, h=3.0, fs=9,
          w_in=4.5):
    fig, ax = fl.figure(w_in, h)
    n = len(rows)
    ax.set_xlim(0, width)
    ax.set_ylim(-0.1, n + 0.8)
    ax.axis("off")
    for x, hd in zip(cols, heads):
        ax.text(x + 0.05, n + 0.4, hd, va="center", fontsize=9.5,
                fontweight="bold", color=fl.INK)
    for i, cells in enumerate(rows):
        y = n - 1 - i
        tok = (toks or ["ops"] * n)[i]
        ax.add_patch(Rectangle((0.0, y + 0.06), width, 0.88,
                               facecolor=fl.FILL[tok], edgecolor=fl.C[tok],
                               lw=1.5 if tok != "ops" else 0.75))
        for j, (x, s) in enumerate(zip(cols, cells)):
            ax.text(x + 0.05, y + 0.5, s, va="center", fontsize=fs,
                    color=fl.INK, fontweight="bold" if j == 0 else None)
    return fig, ax
