"""Dead letters and poison messages.

A transient failure is retried with a limit. A message that still
fails, or that can never succeed, is quarantined: the original bytes,
their hash, the error, the attempts, and an owner. Quarantine is at
the smallest ordering scope, one itinerary: later messages for that
itinerary are parked behind it, and every other itinerary keeps
moving. Replay after a fix runs the parked messages in order through
the same inbox, so a replay that is run twice changes nothing.
"""
from __future__ import annotations

import hashlib
import json
from collections import deque
from dataclasses import dataclass, field

from .inbox import Inbox


class Transient(Exception):
    """Worth retrying: a timeout, a 503, a lock."""


class Poison(Exception):
    """Will fail every time: bad bytes, unknown schema, missing field."""


@dataclass
class Letter:
    msg_id: str
    key: str
    raw: bytes
    sha256: str
    error: str
    attempts: int
    owner: str
    parked: list[bytes] = field(default_factory=list)


def parse_v1(raw: bytes) -> dict:
    """The parser as deployed: departure times must carry an offset."""
    try:
        m = json.loads(raw)
        dep = m["dep"]
    except (ValueError, KeyError) as e:
        raise Poison(f"unreadable: {type(e).__name__}") from e
    if dep[-6] not in "+-":
        raise Poison("dep has no UTC offset")
    return m


def parse_v2(raw: bytes) -> dict:
    """The fix: a zone name is accepted and resolved by the schedule
    service, so the message is applied rather than guessed at."""
    m = json.loads(raw)
    if m["dep"][-6] not in "+-":
        m["dep"] = m["dep"] + "@" + m.get("zone", "UNKNOWN")
    return m


class Consumer:
    def __init__(self, name: str, owner: str, max_attempts: int = 5,
                 parse=parse_v1) -> None:
        self.inbox = Inbox(name)
        self.owner = owner
        self.max_attempts = max_attempts
        self.parse = parse
        self.letters: dict[str, Letter] = {}     # key -> letter
        self.log: list[str] = []
        self.retries = 0

    def offer(self, raw: bytes, flaky: int = 0) -> str:
        """Handle one message. flaky: transient failures to simulate
        before the call succeeds."""
        m = json.loads(raw) if raw[:1] == b"{" else {}
        key = m.get("key", "UNKEYED")
        if key in self.letters:
            self.letters[key].parked.append(raw)
            return "parked"
        attempts = 0
        while True:
            attempts += 1
            try:
                if attempts <= flaky:
                    raise Transient("supplier 503")
                msg = self.parse(raw)
                return self.inbox.handle(msg["id"], msg["key"],
                                         msg["seq"], msg["dep"])
            except Transient as e:
                self.retries += 1
                if attempts < self.max_attempts:
                    continue
                return self._quarantine(m, key, raw, str(e), attempts)
            except Poison as e:
                return self._quarantine(m, key, raw, str(e), attempts)

    def _quarantine(self, m, key, raw, error, attempts) -> str:
        self.letters[key] = Letter(m.get("id", "?"), key, raw,
                                   hashlib.sha256(raw).hexdigest(),
                                   error, attempts, self.owner)
        return "dead-lettered"

    def replay(self, key: str, parse) -> list[str]:
        """After the fix: the letter first, then what was parked."""
        letter = self.letters.pop(key)
        if hashlib.sha256(letter.raw).hexdigest() != letter.sha256:
            raise ValueError("stored bytes changed")
        self.parse = parse
        out = []
        for raw in deque([letter.raw, *letter.parked]):
            out.append(self.offer(raw))
        return out
