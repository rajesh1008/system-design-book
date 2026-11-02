"""Session working directories and the cross-read suite.

A `SessionStore` gives each session its own directory (mode 0700) under
a root, and removes it when the session closes. `shared=True` is the
injected failure: every session gets the same scratch directory and
nothing is removed until the worker recycles, which is how the pilot's
document-intake workers were set up on March 10, 2026.

`cross_read_suite` runs seeded interleavings of concurrent sessions.
Each session uploads one scan tagged with its itinerary and then reads
back "the newest upload", the pilot tool's heuristic. A read that
returns another itinerary's scan is a cross-read.
"""
from __future__ import annotations

import os
import shutil
import tempfile
from dataclasses import dataclass, field
from pathlib import Path

from common.clock import FixedClock
from common.rand import seeded

START = "2026-03-10T14:20:00+00:00"   # 09:20 CDT, the pilot's morning


@dataclass
class Session:
    sid: str
    itinerary: str
    workdir: Path
    clock: FixedClock

    def upload(self, name: str, body: bytes) -> Path:
        up = self.workdir / "uploads"
        up.mkdir(exist_ok=True)
        p = up / name
        p.write_bytes(body)
        t = self.clock.now().timestamp()
        os.utime(p, (t, t))
        return p

    def newest_upload(self) -> bytes | None:
        up = self.workdir / "uploads"
        if not up.exists():
            return None
        files = sorted(up.iterdir(),
                       key=lambda p: (p.stat().st_mtime_ns, p.name))
        return files[-1].read_bytes() if files else None


class SessionStore:
    def __init__(self, root: Path, shared: bool = False, clock=None):
        self.root = Path(root)
        self.shared = shared
        self.clock = clock or FixedClock(START)
        self.open_sessions: dict[str, Session] = {}

    def open(self, sid: str, itinerary: str) -> Session:
        if self.shared:
            wd = self.root / "scratch" / "doc-intake"
        else:
            wd = self.root / "sessions" / sid
            if wd.exists():
                raise FileExistsError(f"session dir reused: {sid}")
        wd.mkdir(parents=True, exist_ok=True, mode=0o700)
        s = Session(sid, itinerary, wd, self.clock)
        self.open_sessions[sid] = s
        return s

    def close(self, s: Session) -> None:
        self.open_sessions.pop(s.sid, None)
        if not self.shared:
            shutil.rmtree(s.workdir)

    def shared_writable(self) -> list[str]:
        """Writable paths that more than one open session can reach."""
        seen: dict[Path, int] = {}
        for s in self.open_sessions.values():
            seen[s.workdir] = seen.get(s.workdir, 0) + 1
        return sorted(str(p) for p, n in seen.items() if n > 1)

    def leftovers(self) -> int:
        d = self.root / "sessions"
        return sum(1 for _ in d.iterdir()) if d.exists() else 0


@dataclass
class SuiteResult:
    runs: int
    reads: int
    cross_reads: int
    shared_paths_seen: int
    leftovers: int          # scans still on disk after their session closed
    examples: list[tuple[str, str]] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return (self.cross_reads == 0 and self.shared_paths_seen == 0
                and self.leftovers == 0)


def cross_read_suite(runs: int = 10_000, seed: int = 11,
                     shared: bool = False,
                     root: Path | None = None) -> SuiteResult:
    r = seeded(seed, "isolation", "suite")
    tmp = None
    if root is None:
        tmp = tempfile.mkdtemp(prefix="designlab-iso-")
        root = Path(tmp)
    store = SessionStore(root, shared=shared)
    reads = cross = shared_seen = left = 0
    examples: list[tuple[str, str]] = []
    n = 0
    try:
        for run in range(runs):
            k = r.choice((2, 2, 3, 4))
            sessions = []
            for j in range(k):
                n += 1
                itin = f"LTG-{r.randrange(1_000_000, 9_999_999)}"
                sessions.append(store.open(f"s-{n:06d}", itin))
            if store.shared_writable():
                shared_seen += 1
            # each session has two steps, upload then read; interleave
            order: list[tuple[Session, str]] = []
            pending = {s.sid: ["up", "read"] for s in sessions}
            live = list(sessions)
            while live:
                s = r.choice(live)
                step = pending[s.sid].pop(0)
                order.append((s, step))
                if not pending[s.sid]:
                    live.remove(s)
            for s, step in order:
                if step == "up":
                    s.upload(f"passport-{s.sid}.jpg",
                             f"scan:{s.itinerary}".encode())
                else:
                    reads += 1
                    got = s.newest_upload()
                    owner = got.decode().split(":", 1)[1] if got else None
                    if owner != s.itinerary:
                        cross += 1
                        if len(examples) < 3:
                            examples.append((s.itinerary, str(owner)))
            for s in sessions:
                store.close(s)
            for s in sessions:
                if (s.workdir / "uploads" / f"passport-{s.sid}.jpg").exists():
                    left += 1
            if shared and run % 50 == 49:   # the worker recycles
                shutil.rmtree(root / "scratch", ignore_errors=True)
        left += store.leftovers()
    finally:
        if tmp:
            shutil.rmtree(tmp, ignore_errors=True)
    return SuiteResult(runs, reads, cross, shared_seen, left, examples)
