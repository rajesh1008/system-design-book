"""Figure 23.4  Voice turn latency budget.

Reading order: one bar per pipeline, stages left to right, against
the two-second line. Mean stage times over 2,000 simulated turns
(seed 23); the held bar is a streaming turn that says a holding
phrase at 1.2 s while the tool call runs. From inputs.voice.
"""
import statistics
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "04-code" / "designlab"))
import figlib as fl  # noqa: E402
from inputs import voice  # noqa: E402

b = voice.stage_means(voice.simulate(streaming=False))
st = voice.simulate(streaming=True)
s = voice.stage_means([x for x in st if not x.held])
hold_ep = statistics.fmean(x.endpoint for x in st if x.held)
stages = ("endpoint", "asr", "model", "tool", "tts")
names = {"endpoint": "end of speech", "asr": "transcribe",
         "model": "model", "tool": "tool", "tts": "speak"}
tok = {"endpoint": "ops", "asr": "ops", "model": "model", "tool": "ops",
       "tts": "ops"}
bars = [("Batch", [b[k] for k in stages]),
        ("Streaming,\nno hold", [s[k] for k in stages]),
        ("Streaming,\nheld", [hold_ep, 0, 0, 0, voice.HOLD_AT_S])]
fig, ax = fl.figure(4.5, 3.4)
for i, (label, vals) in enumerate(bars):
    y = len(bars) - 1 - i
    left = 0.0
    for j, (k, v) in enumerate(zip(stages, vals)):
        if v <= 0:
            continue
        name = "holding phrase" if label.endswith("held") and k == "tts" \
            else names[k]
        ax.barh(y, v, left=left, height=0.55, color=fl.FILL[tok[k]],
                edgecolor=fl.C[tok[k]], lw=0.75, hatch=fl.HATCH[j])
        if v > 0.45:
            ax.text(left + v / 2, y, name, ha="center", va="center",
                    fontsize=7.5, color=fl.INK, rotation=90 if v < 0.8 else 0)
        left += v
    ax.text(left + 0.08, y, f"{left:.2f} s", va="center", fontsize=9,
            color=fl.INK)
ax.axvline(voice.BUDGET_S, color=fl.C["policy"], ls="--", lw=1.2)
ax.text(voice.BUDGET_S + 0.05, 2.45, "2 s budget", fontsize=9,
        color=fl.LABEL["policy"])
ax.set_yticks(range(len(bars)))
ax.set_yticklabels([x[0] for x in reversed(bars)], fontsize=9.5)
ax.set_xlim(0, 6.2)
ax.set_ylim(-0.5, 2.7)
ax.set_xlabel("Mean seconds from last word to first audio")
fl.save(fig)
