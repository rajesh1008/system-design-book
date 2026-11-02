"""Figure 14.1  Where the time goes in one call.

Reading order: top to bottom, one bar per case, time left to right.
Prefill is the prompt the cache did not hold; decode is 173 output
tokens at a batch of 16. From 04-code/designlab (serving.clocks with
the engine A profile), the same values as serving.demo --part clocks.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "04-code" / "designlab"))
import figlib as fl  # noqa: E402
from serving.bakeoff import engines  # noqa: E402
from serving.clocks import decode_step_s, three_clocks  # noqa: E402

e = engines()["engines"]["engine-a"]
itl = decode_step_s(16, e["decode_base_ms"], e["decode_per_seq_ms"])
rows = []
for label, cached in (("Cold prompt", 0), ("Warm prompt, 78% cached",
                                           round(6217 * 0.78))):
    c = three_clocks(0.0, 6217, cached, 173, e["prefill_tok_s"], itl)
    rows.append((label, c.ttft_s, c.e2e_s - c.ttft_s))
fig, ax = fl.figure(4.5, 3.0)
for i, (label, pre, dec) in enumerate(rows):
    y = 1 - i
    ax.barh(y, pre, color=fl.FILL["model"], edgecolor=fl.C["model"],
            lw=0.75, height=0.5, hatch="///")
    ax.barh(y, dec, left=pre, color=fl.FILL["ops"], edgecolor=fl.C["ops"],
            lw=0.75, height=0.5)
    ax.text(pre + dec + 0.08, y, f"{pre + dec:.2f} s", va="center",
            fontsize=9.5, color=fl.INK)
    ax.text(0.02, y + 0.36, f"{label}: prefill {pre:.2f} s",
            fontsize=9.5, color=fl.INK)
ax.text(1.6, -0.62, "decode: 173 tokens, one step each", fontsize=9.5,
        color=fl.LABEL["ops"])
ax.set_yticks([])
ax.set_ylim(-0.9, 1.6)
ax.set_xlim(0, 5.2)
ax.set_xlabel("Seconds for one call, batch of 16")
fl.save(fig)
