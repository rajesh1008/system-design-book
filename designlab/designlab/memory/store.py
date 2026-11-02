"""The governed memory store.

`write` refuses a draft that cannot name its source event, its scope,
and its confidence (the chain's `Refused`, so a refusal reads like any
other missing evidence). The tenant comes from the `SessionToken`; a
draft has no tenant field. A second value for the same head key must
say which head it read (compare-and-set): a writer that read an older
head gets `StaleHead`, and a value observed before the head's own
observation gets `OlderThanHead`, so an old note cannot overwrite a
newer one. The old version stays, marked superseded, for history.

`read` returns only the caller's tenant, only scopes that apply to
the caller's session and itinerary, and only what the caller's role
may see (policy.READ_POLICY). Asking for another tenant raises the
isolation package's `OutOfScope`.
"""
from __future__ import annotations

from dataclasses import dataclass, replace
from datetime import datetime, timedelta

from chain.record import Refused
from isolation.blast import OutOfScope

from .record import (Draft, MemoryRecord, SCOPES, KINDS, STANDING_KINDS,
                     HIGH_CONSEQUENCE)

RETENTION_DAYS = 180          # memory-retention-v1, from November 3, 2025
TRIP_DAYS_DEFAULT = 30


class WriteRefused(Refused):
    """A memory write without the evidence a memory needs."""


class OlderThanHead(WriteRefused):
    """The draft was observed before the value it would replace."""


class StaleHead(Exception):
    def __init__(self, key: tuple, expected, head):
        self.key, self.expected, self.head = key, expected, head
        super().__init__(f"stale head: expected {expected}, head is {head}")


@dataclass(frozen=True)
class SessionToken:
    """Issued at sign-in by identity, not built from conversation text."""
    session_id: str
    tenant: str              # the traveler named on the itinerary
    itinerary: str
    role: str = "agent-loop"


def _iso(dt: datetime) -> str:
    return dt.isoformat()


class MemoryStore:
    def __init__(self, clock, trail, trip_ends: dict | None = None,
                 retention_days: int = RETENTION_DAYS):
        self.clock = clock
        self.trail = trail
        self.trip_ends = trip_ends or {}
        self.retention = timedelta(days=retention_days)
        self.records: dict[str, MemoryRecord] = {}
        self.heads: dict[tuple, str] = {}
        self.tombstones: list[dict] = []
        self._n = 0

    # ---------------------------------------------------------- write path
    def check(self, draft: Draft) -> list[str]:
        """What the draft lacks (empty when it may be written)."""
        missing = []
        src = draft.source
        if src is None or not src.event_id:
            missing.append("provenance: source event")
        elif src.kind not in KINDS:
            missing.append(f"provenance: unknown kind {src.kind}")
        if draft.scope not in SCOPES:
            missing.append("scope")
        if draft.confidence is None:
            missing.append("confidence")
        if draft.scope == "trip" and not draft.trip:
            missing.append("scope: trip without an itinerary")
        if (draft.scope == "standing" and src is not None
                and src.kind not in STANDING_KINDS):
            missing.append("scope: standing needs the customer's "
                           "confirmation")
        if (draft.subject in HIGH_CONSEQUENCE and src is not None
                and src.kind == "agent-inferred"):
            missing.append(f"source: {draft.subject} is never inferred")
        return missing

    def write(self, token: SessionToken, draft: Draft,
              expected_head: str | None = None) -> MemoryRecord:
        missing = self.check(draft)
        if missing:
            self._refuse(token, draft, missing)
            raise WriteRefused(missing)
        if draft.scope == "trip" and draft.trip != token.itinerary:
            self._refuse(token, draft, ["trip is not this session's"])
            raise OutOfScope(draft.trip)
        now = self.clock.now()
        observed = draft.observed_at or _iso(now)
        key = (token.tenant, draft.subject, draft.scope, draft.trip)
        head_id = self.heads.get(key)
        head = self.records.get(head_id) if head_id else None
        if head_id != expected_head:
            self.trail.append({"kind": "memory.stale_head",
                               "tenant": token.tenant,
                               "subject": draft.subject,
                               "expected": expected_head, "head": head_id})
            raise StaleHead(key, expected_head, head_id)
        if head is not None and observed < head.observed_at:
            reason = [f"older than head {head.memory_id}"]
            self._refuse(token, draft, reason)
            raise OlderThanHead(reason)
        self._n += 1
        rec = MemoryRecord(
            memory_id=f"MR-{self._n:05d}", tenant=token.tenant,
            session_id=token.session_id, subject=draft.subject,
            value=draft.value, scope=draft.scope, trip=draft.trip,
            source=draft.source, confidence=float(draft.confidence),
            observed_at=observed, recorded_at=_iso(now),
            expires_at=self._expiry(draft, now),
            version=head.version + 1 if head else 1,
            supersedes=head.memory_id if head else None,
            derived_from=tuple(draft.derived_from))
        if head is not None:
            self.records[head.memory_id] = replace(
                head, status="superseded", superseded_by=rec.memory_id)
        self.records[rec.memory_id] = rec
        self.heads[key] = rec.memory_id
        self.trail.append({"kind": "memory.write", "memory": rec.memory_id,
                           "tenant": rec.tenant, "subject": rec.subject,
                           "scope": rec.scope, "source": rec.source.event_id,
                           "source_kind": rec.source.kind,
                           "supersedes": rec.supersedes})
        return rec

    def head(self, token: SessionToken, subject: str, scope: str,
             trip: str | None = None) -> str | None:
        return self.heads.get((token.tenant, subject, scope, trip))

    def _expiry(self, draft: Draft, now: datetime) -> str | None:
        if draft.scope == "session":
            return None                      # ends with the session
        if draft.scope == "trip":
            end = self.trip_ends.get(draft.trip)
            return end or _iso(now + timedelta(days=TRIP_DAYS_DEFAULT))
        return _iso(now + self.retention)

    def _refuse(self, token, draft, missing) -> None:
        self.trail.append({"kind": "memory.refused",
                           "tenant": token.tenant,
                           "subject": draft.subject,
                           "missing": list(missing)})

    # ----------------------------------------------------------- read path
    def read(self, token: SessionToken, subject: str | None = None,
             tenant: str | None = None) -> list[MemoryRecord]:
        from .policy import can_read
        if tenant is not None and tenant != token.tenant:
            self.trail.append({"kind": "memory.read_denied",
                               "tenant": token.tenant, "asked": tenant})
            raise OutOfScope(tenant)
        now = _iso(self.clock.now())
        out = []
        for r in self.records.values():
            if r.tenant != token.tenant or r.status != "active":
                continue
            if subject is not None and r.subject != subject:
                continue
            if r.expires_at is not None and r.expires_at <= now:
                continue
            if r.scope == "session" and r.session_id != token.session_id:
                continue
            if r.scope == "trip" and r.trip != token.itinerary:
                continue
            if can_read(token.role, r):
                out.append(r)
        return sorted(out, key=lambda r: r.memory_id)

    def history(self, token: SessionToken, subject: str) -> list:
        """Every version, superseded included, for roles that may see it."""
        from .policy import can_read_history
        if not can_read_history(token.role):
            return []
        return sorted((r for r in self.records.values()
                       if r.tenant == token.tenant and r.subject == subject
                       and r.status != "deleted"),
                      key=lambda r: r.memory_id)

    def close_session(self, token: SessionToken) -> int:
        n = 0
        for r in list(self.records.values()):
            if (r.session_id == token.session_id and r.scope == "session"
                    and r.status == "active"):
                self.delete(r.memory_id, "session closed")
                n += 1
        return n

    # ---------------------------------------------------------- deletion
    def delete(self, memory_id: str, reason: str) -> None:
        r = self.records[memory_id]
        self.records[memory_id] = replace(r, status="deleted", value="")
        for k, v in list(self.heads.items()):
            if v == memory_id:
                del self.heads[k]
        stone = {"memory": memory_id, "tenant": r.tenant,
                 "reason": reason, "at": _iso(self.clock.now())}
        self.tombstones.append(stone)
        self.trail.append({"kind": "memory.delete", **stone})
