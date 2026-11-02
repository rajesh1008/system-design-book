"""Spans and a small tracer with a simulated clock.

A span is one timed operation with a parent, a name, attributes and a
status. Content (prompts, tool arguments and results) is not put on
attributes: the tracer keeps it in a separate evidence store keyed by
span, and the span carries only a reference and a digest. That is the
conventions' recommended pattern for production: off by default,
stored externally, referenced from the span.
"""
from __future__ import annotations

import hashlib
import json
from contextlib import contextmanager
from dataclasses import asdict, dataclass, field
from datetime import datetime, timedelta

from . import conventions as c

BASE = "2026-06-16T09:00:00-05:00"     # CDT


def digest(obj) -> str:
    raw = json.dumps(obj, sort_keys=True, default=str)
    return hashlib.sha256(raw.encode()).hexdigest()[:16]


@dataclass
class Span:
    trace_id: str
    span_id: str
    parent_id: str | None
    name: str
    kind: str = "INTERNAL"
    start_ms: int = 0
    end_ms: int = 0
    attrs: dict = field(default_factory=dict)
    status: str = "OK"

    @property
    def ms(self) -> int:
        return self.end_ms - self.start_ms

    def to_json(self) -> str:
        return json.dumps(asdict(self), sort_keys=True, default=str)

    @staticmethod
    def from_json(line: str) -> "Span":
        return Span(**json.loads(line))


class Tracer:
    """Builds one trace. `skip` names span kinds this tracer does not
    emit, which is how an uninstrumented component looks from here."""

    def __init__(self, key: str, start_ms: int = 0,
                 skip: tuple[str, ...] = ()):
        self.trace_id = hashlib.sha256(key.encode()).hexdigest()[:32]
        self.now_ms = start_ms
        self.spans: list[Span] = []
        self.evidence: dict[str, dict] = {}
        self.skip = set(skip)
        self._stack: list[Span] = []
        self._n = 0

    def advance(self, ms: int) -> None:
        self.now_ms += int(ms)

    @contextmanager
    def span(self, name: str, kind: str = "INTERNAL", **attrs):
        if c.kind_of(name) in self.skip:
            yield None
            return
        self._n += 1
        sid = hashlib.sha256(
            f"{self.trace_id}:{self._n}".encode()).hexdigest()[:16]
        parent = self._stack[-1].span_id if self._stack else None
        s = Span(self.trace_id, sid, parent, name, kind, self.now_ms,
                 self.now_ms, dict(attrs))
        self.spans.append(s)
        self._stack.append(s)
        try:
            yield s
        except Exception:
            s.status = "ERROR"
            raise
        finally:
            self._stack.pop()
            s.end_ms = self.now_ms

    def record(self, s: Span | None, inp, out) -> None:
        """Content goes to the evidence store, not onto the span."""
        if s is None:
            return
        self.evidence[s.span_id] = {"in": inp, "out": out}
        s.attrs[c.IO_REF] = f"evidence://{self.trace_id[:8]}/{s.span_id}"
        s.attrs[c.ARGS_DIGEST] = digest(inp)


def clock_at(ms: int) -> str:
    t = datetime.fromisoformat(BASE) + timedelta(milliseconds=ms)
    return t.isoformat(timespec="seconds")


def export(spans: list[Span], evidence: dict) -> str:
    """One trace as JSON lines: spans, then one evidence line."""
    lines = [s.to_json() for s in spans]
    lines.append(json.dumps({"evidence": evidence}, sort_keys=True,
                            default=str))
    return "\n".join(lines) + "\n"


def load(text: str) -> tuple[list[Span], dict]:
    spans, evidence = [], {}
    for line in text.splitlines():
        d = json.loads(line)
        if "evidence" in d:
            evidence = d["evidence"]
        else:
            spans.append(Span(**d))
    return spans, evidence


def children(spans: list[Span]) -> dict[str | None, list[Span]]:
    out: dict[str | None, list[Span]] = {}
    for s in spans:
        out.setdefault(s.parent_id, []).append(s)
    return out
