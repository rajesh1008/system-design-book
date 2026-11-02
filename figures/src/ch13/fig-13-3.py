"""Figure 13.3  Output variance on golden inputs.

Reading order: top panel first. Distinct raw texts per golden case
across repeated identical calls (refund-reason 1.3; 10 samples on the
small model at its default sampling, 8 on the dated small model at
temperature 0 and 1). The decision never moved. Bottom panel: the
refund amount when the model was asked to compute it, 26 answers, one
wrong by 22 cents. Recorded live November 2, 2026; seed 2026 unused.
"""
import figlib as fl

cases = ["rr-01", "rr-05", "rr-07", "rr-10", "rr-12"]
small = [1, 4, 1, 1, 3]
t0 = [1, 1, 1, 1, 1]
t1 = [1, 1, 1, 3, 2]
fig, (ax, bx) = fl.figure(4.5, 3.6, nrows=2,
                          gridspec_kw={"height_ratios": [2.2, 1]})
w = 0.26
xs = range(len(cases))
for k, (vals, lab, tok, h) in enumerate(
        [(small, "small, default", "model", ""),
         (t0, "dated, temp 0", "org", "..."),
         (t1, "dated, temp 1", "org", "///")]):
    ax.bar([x + (k - 1) * w for x in xs], vals, w, color=fl.FILL[tok],
           edgecolor=fl.C[tok], hatch=h, lw=fl.STROKE["data"], label=lab)
ax.set_xticks(list(xs))
ax.set_xticklabels(cases)
ax.set_ylabel("Distinct texts")
ax.set_ylim(0, 6.2)
ax.legend(loc="upper right", frameon=False, ncol=3, fontsize=9,
          bbox_to_anchor=(1.0, 1.02))
ax.text(1.45, 4.7, "decision identical in all 140 samples",
        fontstyle="italic", fontsize=9)
rows = [("mid, am-01", 3, 0), ("mid, am-02", 3, 0),
        ("small, am-01", 10, 0), ("small, am-02", 9, 1)]
ys = list(range(len(rows)))[::-1]
for y, (lab, ok, bad) in zip(ys, rows):
    bx.barh(y, ok, color=fl.FILL["model"], edgecolor=fl.C["model"],
            lw=fl.STROKE["data"])
    if bad:
        bx.barh(y, bad, left=ok, color=fl.FILL["fail"],
                edgecolor=fl.C["fail"], hatch="xx", lw=fl.STROKE["data"])
        bx.text(ok + bad + 0.2, y, "1814.52, 22 cents short",
                va="center", fontsize=9, color=fl.LABEL["fail"])
bx.set_yticks(ys)
bx.set_yticklabels([r[0] for r in rows], fontsize=9)
bx.set_xlim(0, 16)
bx.set_xlabel("Model-computed refund answers")
fl.save(fig)
