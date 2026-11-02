"""One pool of recorded calls for the whole chapter.

Every request is looked up by its body hash, first in Chapter 13's
change-intent fixtures (the frontier answers that chapter recorded),
then in this chapter's pool. Offline, a miss is an error, as in
Chapter 13. Live, a miss is sent once, timed, redacted, and written to
the pool, and only those calls count against the live spend cap, so a request the gate already paid for is never paid for
again by the router check.
"""
from __future__ import annotations

import json
from pathlib import Path

from common.client import FixtureTransport, NoFixture, body_hash
from common.models import pin
from common.redact import redact

from models.runner import FIXTURE_DIR as CH13_FIXTURES
from models.runner import TimedTransport

HERE = Path(__file__).resolve().parent
POOL = HERE / "fixtures" / "calls"


class PoolTransport:
    def __init__(self, pool: Path = POOL, live=None, live_meter=None):
        self.pool = Path(pool)
        self.sources = [FixtureTransport(CH13_FIXTURES / "change-intent")]
        if self.pool.exists():
            self.sources.append(FixtureTransport(self.pool))
        self.live = TimedTransport(live) if live is not None else None
        self.sent = 0
        self.live_meter = live_meter
        self.written: dict[str, dict] = {}

    def __call__(self, body: dict) -> dict:
        h = body_hash(body)
        for src in self.sources:
            if h in src.by_hash:
                return src.by_hash[h]
        if h in self.written:
            return self.written[h]
        if self.live is None:
            raise NoFixture(f"no recorded response for request {h}")
        p = pin(body["model"])
        if self.live_meter is not None:
            self.live_meter.check(p, len(json.dumps(body)),
                                  body.get("max_tokens", 0))
        resp = self.live(body)
        if self.live_meter is not None:
            self.live_meter.record(p, resp.get("usage", {}))
        self.sent += 1
        self.pool.mkdir(parents=True, exist_ok=True)
        rec = redact({"request_hash": h, "request": body,
                      "response": resp})
        (self.pool / f"{h}.json").write_text(
            json.dumps(rec, indent=2, sort_keys=True) + "\n")
        self.written[h] = resp
        return resp
