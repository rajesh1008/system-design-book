"""Chapter 23 lab: inputs as data, contracts at the edge.

    python3 -m inputs.demo --part opening
    python3 -m inputs.demo --part letter [--inject instruction-as-text]
    python3 -m inputs.demo --part boarding [--conf 0.62]
    python3 -m inputs.demo --part vision      # recorded model read
    python3 -m inputs.demo --part thresholds
    python3 -m inputs.demo --part voice [--budget 2.0] [--batch]
    python3 -m inputs.demo --part readback [--off]
    python3 -m inputs.demo --part web [--page FILE]
    python3 -m inputs.demo --part edge
    python3 -m inputs.demo --part card
"""
from __future__ import annotations

import argparse
from pathlib import Path

from common.text import emit

from . import voice
from .contract import CONTRACTS, MODALITIES
from .edge import INTAKE_PATHS, NotAdmitted, adapter, admit, for_context
from .pilot import run as pilot_run
from .route import population, sweep
from .samples import (CDT, RawInput, boarding_pass, letter, opening,
                      voice_note)
from .web import NOTICE, notice_input, read


def show(text: str) -> None:
    for line in text.splitlines():
        emit(line)


def part_opening(a) -> None:
    for raw in opening():
        env = admit(raw)
        show(for_context(env))
        for layer in raw.layers:
            if not layer.visible:
                emit(f"  hidden layer at {layer.where}")
        bad = [f"{f.name}: {', '.join(f.reasons)}" for f in
               env.fields.values() if f.reasons]
        for b in bad:
            emit(f"  check  {b}")
        if env.read_back:
            emit(f"  read back before use: {', '.join(env.read_back)}")
        emit(f"  kept out of the agent's view: {env.quarantined} chars")
        emit("")


def part_letter(a) -> None:
    r = pilot_run(letter(), a.inject)
    p = r["proposal"]
    path = "pilot (text as instruction)" if a.inject else "contract"
    emit(f"path: {path}")
    if r["envelope"] is not None:
        show(for_context(r["envelope"]))
    emit(f"proposal: refund {p.amount:.2f} on {p.locator} to card "
         f"{p.card}")
    emit(f"  card source: {p.source}; skip approval: {p.skip_approval}")
    if r["refusals"]:
        for x in r["refusals"]:
            emit(f"  gateway refuses: {x}")
    else:
        emit("  gateway: passes; refunds-v3 sends it for approval")


def part_boarding(a) -> None:
    raw = boarding_pass(a.conf)
    env = admit(raw)
    show(for_context(env))
    for f in env.fields.values():
        if f.reasons:
            emit(f"  {f.name}: {', '.join(f.reasons)}")


def part_vision(a) -> None:
    from models.vision import FIELDS, extract
    out, comp, _ = extract(record=False)
    f, c = out.get("fields", {}), out.get("confidence", {})
    raw = RawInput("in-lab-bp-02", "boarding-pass", "chat-upload",
                   "session c-90114", "2026-05-27T07:48:15" + CDT,
                   boarding_pass().layers,
                   {k: (str(f.get(k)), float(c.get(k) or 0.0), "model")
                    for k in FIELDS if f.get(k)}, comp.model)
    env = admit(raw)
    show(for_context(env))
    emit(f"  model flag instruction_like: {out.get('instruction_like')}")
    emit(f"  record check: {sum(not x.reasons for x in env.fields.values())}"
         f" of {len(env.fields)} fields agree with booking HN8C2V")


def part_thresholds(a) -> None:
    rows = sweep(population())
    emit("2,000 seeded reads; accept at or above the threshold")
    emit("  thresh  accepted  err      +record  err      review")
    for r in rows:
        emit(f"  {r['t']:.2f}    {r['accepted']:>6.1%}  {r['err']:>6.2%}"
             f"   {r['accepted_chk']:>6.1%}  {r['err_chk']:>6.2%}  "
             f"{r['review']:>6}")
    emit(f"  below 0.60, asked again: {rows[0]['ask']}")


def part_voice(a) -> None:
    turns = voice.simulate(streaming=not a.batch)
    s = voice.summary(turns)
    m = voice.stage_means(turns)
    kind = "batch" if a.batch else "streaming"
    emit(f"{s['n']:,} simulated turns, {kind} pipeline")
    emit(f"  first audio p50 {s['p50']:.2f} s, p95 {s['p95']:.2f} s, "
         f"max {s['max']:.2f} s")
    emit(f"  over the {a.budget:.1f} s budget: "
         f"{sum(t.total > a.budget for t in turns)}")
    if not a.batch:
        emit(f"  holding phrase spoken: {s['held']} "
             f"({s['held'] / s['n']:.0%})")
    items = [f"{k} {v:.2f}" for k, v in m.items()]
    emit("  mean stage, s: " + ", ".join(items[:3]))
    emit("                 " + ", ".join(items[3:]))


def part_readback(a) -> None:
    r = voice.read_back(enabled=not a.off)
    emit(f"{r['values']:,} spoken amounts and dates, "
         f"read-back {'off' if a.off else 'on'}")
    emit(f"  misheard by transcription: {r['misheard']}")
    emit(f"  wrong value reached a proposal: {r['reached']}")
    emit(f"  read-backs spoken: {r['read_backs']:,}; "
         f"to a person: {r['to_person']}")
    env = admit(voice_note())
    emit(f"voice note {env.provenance.input_id}: route {env.route}")
    for f in env.fields.values():
        emit(f"  {f.name:<9} {f.value:<11} {f.confidence:.2f} {f.route}"
             + (f"  ({'; '.join(f.reasons)})" if f.reasons else ""))
    emit(f"  read back before use: {', '.join(env.read_back)}")


def part_web(a) -> None:
    html = Path(a.page).read_text() if a.page else NOTICE
    visible, hidden = read(html)
    emit(f"visible text: {len(visible)} chars; hidden: {len(hidden)}")
    for where, text in hidden:
        emit(f"  {where:<14} {text[:48]}")
    env = admit(notice_input(html))
    show(for_context(env))


def part_edge(a) -> None:
    emit(f"intake paths: {len(INTAKE_PATHS)}")
    tagged = 0
    samples = {r.channel: r for r in (opening() + (letter(),
               boarding_pass(), notice_input()))}
    for path in INTAKE_PATHS:
        raw = samples.get(path)
        if raw is None:
            raw = RawInput(f"probe-{path}", "customer-letter", path,
                           "edge test", "2026-05-15T09:00:00" + CDT,
                           opening()[0].layers, {})
        env = adapter(path)(raw)
        ok = env.trust == "untrusted" and bool(env.provenance.sha256)
        tagged += ok
        emit(f"  {path:<17} {env.trust:<10} sha256 "
             f"{env.provenance.sha256[:10]}")
    emit(f"tagged untrusted at the edge: {tagged} of {len(INTAKE_PATHS)}")
    try:
        for_context("Please send the refund to card ending 7731.")
    except NotAdmitted as e:
        emit(f"raw text to the assembler: refused ({e})")


def part_card(a) -> None:
    mods = sorted({c.modality for c in CONTRACTS.values()})
    emit("Input card, May 2026 (lab)")
    emit(f"  modalities under contract: {len(mods)} of {len(MODALITIES)}"
         f" ({', '.join(mods)})")
    emit(f"  contracts: {len(CONTRACTS)}; free-text fields: "
         f"{sum(c.free_text for c in CONTRACTS.values())}")
    emit(f"  intake paths through the edge: {len(INTAKE_PATHS)}")
    s = voice.summary(voice.simulate())
    emit(f"  voice turn p95 (simulation): {s['p95']:.1f} s")
    rb = voice.read_back()
    emit(f"  amounts and dates read back: {rb['values']:,} of "
         f"{rb['values']:,}")


PARTS = {"opening": part_opening, "letter": part_letter,
         "boarding": part_boarding, "vision": part_vision,
         "thresholds": part_thresholds, "voice": part_voice,
         "readback": part_readback, "web": part_web, "edge": part_edge,
         "card": part_card}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--part", choices=sorted(PARTS), default="opening")
    ap.add_argument("--inject", choices=["instruction-as-text"])
    ap.add_argument("--conf", type=float, default=0.97)
    ap.add_argument("--budget", type=float, default=voice.BUDGET_S)
    ap.add_argument("--batch", action="store_true")
    ap.add_argument("--off", action="store_true")
    ap.add_argument("--page")
    a = ap.parse_args(argv)
    PARTS[a.part](a)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
