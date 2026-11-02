"""Two fixture runtimes with different session models.

`threads` keeps one thread per case and a checkpoint after every step.
`sessions` starts a session per invocation and keeps an event log; a
session ends after eight hours. Each saves its own native state in its
own format, and neither can read the other's: that is the part of a
runtime a team rents, and the part that does not move.

Both run the same harness step function. The harness never sees a
thread id or a session id; it sees its own run id, which is the case.
"""
from __future__ import annotations

import itertools
import json
from pathlib import Path

FIXTURES = Path(__file__).with_name("fixtures")


class NotPortable(Exception):
    """A runtime was handed native state it cannot read."""


def fixture(name: str) -> dict:
    return json.loads((FIXTURES / f"{name}.json").read_text())


class Adapter:
    name = ""

    def __init__(self):
        self.spec = fixture(self.name)
        self.native: dict = {}          # run id -> native state
        self._ids = itertools.count(1)

    @property
    def native_fields(self) -> list:
        return self.spec["native_fields"]

    def handle(self, run_id: str) -> str:
        raise NotImplementedError

    def save_native(self, run_id: str, state: dict) -> None:
        raise NotImplementedError

    def export(self, run_id: str) -> dict:
        raise NotImplementedError

    def import_native(self, blob: dict) -> dict:
        if blob.get("format") != self.spec["export_format"]:
            raise NotPortable(f"{self.name} cannot read "
                              f"{blob.get('format')}")
        return blob["state"]

    def run(self, run_id: str, state: dict, advance, stop_after=None):
        """Drive the harness until it closes or the worker is killed
        after `stop_after` steps. Returns (state, killed)."""
        steps = 0
        while not state.get("closed"):
            if stop_after is not None and steps >= stop_after:
                return state, True
            state = advance(state, self.handle(run_id))
            self.save_native(run_id, state)
            steps += 1
        return state, False


class Threads(Adapter):
    name = "threads"

    def handle(self, run_id):
        return self.native.setdefault(run_id, {
            "thread_id": f"th-{run_id}", "checkpoints": []})["thread_id"]

    def save_native(self, run_id, state):
        t = self.native[run_id]
        t["checkpoints"].append(
            {"checkpoint_id": f"cp-{len(t['checkpoints']) + 1:02d}",
             "values": dict(state)})

    def export(self, run_id):
        return {"format": self.spec["export_format"],
                "state": self.native[run_id]["checkpoints"][-1]["values"]}


class Sessions(Adapter):
    name = "sessions"

    def handle(self, run_id):
        s = self.native.get(run_id)
        if s is None or s.get("ended"):
            s = self.native[run_id] = {
                "session_id": f"ss-{next(self._ids):04d}", "events": []}
        return s["session_id"]

    def save_native(self, run_id, state):
        s = self.native[run_id]
        s["events"].append({"event_id": f"ev-{len(s['events']) + 1:04d}",
                            "state": dict(state)})

    def export(self, run_id):
        return {"format": self.spec["export_format"],
                "state": self.native[run_id]["events"][-1]["state"]}


ADAPTERS = {"threads": Threads, "sessions": Sessions}
