"""Figure 5.3  Estimation sheet with assumptions.

Reading order: top to bottom, seven inputs then six derived lines, as
the review read them. Values computed by method.design from v0_1.toml;
the last two rows, the ones the review argued about, are marked.
"""
import sys
from pathlib import Path

import figlib as fl
from matplotlib.patches import Rectangle

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "04-code" / "designlab"))
from method.design import load  # noqa: E402

d = load("v0_1")
vals = d.values
INPUTS = [("changes_per_year", "changes a year", "baseline"),
          ("storm_days", "average days", "queue reports"),
          ("window_hours", "hours", "queue reports"),
          ("calls_per_change", "model calls", "pilot traces"),
          ("tools_per_change", "tool calls", "pilot traces"),
          ("refund_share", "of changes", "change mix"),
          ("reviews_per_hour", "per person-hour", "supervisors")]
DERIVED = [("avg_per_day", "changes a day"), ("storm_per_hour", "changes an hour"),
           ("storm_per_s", "changes a second"), ("peak_requests_per_s", "requests a second"),
           ("approvals_per_hour", "approvals an hour"), ("reviewers_needed", "reviewers")]


def fmt(v):
    if v >= 100:
        return f"{v:,.0f}"
    if v >= 10:
        return f"{v:.1f}"
    return f"{v:g}" if v == int(v) else f"{v:.2f}"


rows = [("in", n, u, s) for n, u, s in INPUTS] + [("=", n, u, "") for n, u in DERIVED]
fig, ax = fl.figure(4.5, 4.4)
n = len(rows)
ax.set_xlim(0, 10)
ax.set_ylim(-0.9, n + 0.9)
ax.axis("off")
ax.text(0.1, n + 0.4, "Line", fontweight="bold", va="center")
ax.text(6.9, n + 0.4, "Value", fontweight="bold", va="center", ha="right")
ax.text(7.2, n + 0.4, "Source", fontweight="bold", va="center")
for i, (kind, name, unit, src) in enumerate(rows):
    y = n - i - 0.5
    hot = name in ("approvals_per_hour", "reviewers_needed")
    tok = "fail" if hot else ("ops" if kind == "in" else "evidence")
    ax.add_patch(Rectangle((0, y - 0.45), 10, 0.9, facecolor=fl.FILL[tok] if hot or kind == "=" else "white",
                           edgecolor=fl.C[tok] if hot else fl.GREY_LIGHT,
                           lw=fl.STROKE["control" if hot else "data"]))
    ax.text(0.1, y, name, va="center", fontfamily=fl.PAL["fonts"]["mono"], fontsize=9)
    ax.text(6.9, y, fmt(vals[name]), va="center", ha="right")
    ax.text(7.2, y, src if src else unit, va="center", fontsize=9.5,
            fontstyle="normal" if src else "italic")
ax.text(5, -0.55, "Marked rows: the two the review argued about", ha="center",
        fontsize=9.5, fontstyle="italic")
fl.save(fig)
