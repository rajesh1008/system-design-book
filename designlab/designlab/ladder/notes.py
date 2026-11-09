"""Answer notes: what a candidate said and drew, minute by minute.

An interviewer's note is the record the rubric scores. Each line is an
event with a minute (`at`) and a kind: frame, question, estimate,
chain, gap, note, tradeoff, cost, record, model, or component.
"""
from __future__ import annotations

import copy
import tomllib
from pathlib import Path

DATA = Path(__file__).resolve().parent / "data" / "answers"


def load(aid: str) -> dict:
    return tomllib.loads((DATA / f"{aid}.toml").read_text())


def load_all() -> dict[str, dict]:
    return {p.stem: load(p.stem) for p in sorted(DATA.glob("A*.toml"))}


def events(note: dict, kind: str | None = None,
           by: int | None = None) -> list[dict]:
    out = []
    for ev in note.get("said", []):
        if kind and ev["kind"] != kind:
            continue
        if by is not None and ev["at"] > by:
            continue
        out.append(ev)
    return out


def shows(note: dict, by: int | None = None) -> set[str]:
    tags: set[str] = set()
    for ev in events(note, by=by):
        tags.update(ev.get("shows", []))
    return tags


def without(note: dict, kind: str) -> dict:
    """A copy of the note with every event of one kind removed."""
    out = copy.deepcopy(note)
    out["said"] = [e for e in out["said"] if e["kind"] != kind]
    return out


def minutes_on(note: dict, kind: str, end: int = 45) -> int:
    """Minutes spent on one kind: from each event to the next event."""
    said = sorted(note["said"], key=lambda e: e["at"])
    total = 0
    for ev, nxt in zip(said, said[1:] + [{"at": end}]):
        if ev["kind"] == kind:
            total += max(0, min(nxt["at"], end) - ev["at"])
    return total


def as_text(note: dict) -> str:
    """The note as a plain transcript, for a person or a model."""
    lines = []
    for ev in sorted(note["said"], key=lambda e: e["at"]):
        k, at = ev["kind"], ev["at"]
        if k == "component":
            body = "named components: " + ", ".join(ev["names"])
        elif k == "gap":
            who = ev.get("owner") or "no owner"
            body = f"{ev['gap']} ({who}): {ev['text']}"
        elif k == "chain":
            body = "drew: " + ev["text"]
        elif k == "frame":
            eff = ", ".join(ev.get("effects", [])) or "none named"
            who = ev.get("owner") or "none named"
            body = (f"frame: {ev['text']} (effects: {eff}; "
                    f"owner: {who})")
        elif k == "estimate":
            src = ev.get("source") or "no source given"
            body = f"estimate: {ev['text']} (source: {src})"
        else:
            body = f"{k}: {ev.get('text', '')}"
        lines.append(f"[{at:02d} min] {body}")
    return "\n".join(lines)
