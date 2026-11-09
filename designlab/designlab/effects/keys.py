"""Idempotency keys, minted by the control plane (Chapter 7).

A key names one permitted effect. It is derived from the permission id,
the tool and the request's fingerprint, so:

    the same permission and request always get the same key
    a second, separately permitted effect gets a different key
    a permission cannot be keyed for a request it did not cover

The executor never mints a key. If it did, a retry loop around the call
would mint a fresh key per attempt, and every retry would look new.
"""
from __future__ import annotations

import hashlib
from dataclasses import dataclass

from chain.record import Permission
from corpus.tools import fingerprint


class KeyRefused(Exception):
    """The control plane will not key this request."""


@dataclass(frozen=True)
class EffectKey:
    key: str
    permission_id: str
    tool: str
    fingerprint: str
    minted_at: float   # seconds on the run clock


class KeyIssuer:
    """Lives in the control plane, next to the policy engine."""

    def __init__(self) -> None:
        self._issued: dict[tuple[str, str], EffectKey] = {}

    def mint(self, permission: Permission, tool: str, request: dict,
             at: float = 0.0) -> EffectKey:
        if permission is None:
            raise KeyRefused("no permission, no key")
        fp = fingerprint(request)
        slot = (permission.permission_id, tool)
        old = self._issued.get(slot)
        if old is not None:
            if old.fingerprint != fp:
                raise KeyRefused(f"{permission.permission_id} is already "
                                 f"keyed for a different {tool} request")
            return old
        raw = f"{permission.permission_id}|{tool}|{fp}".encode()
        key = "idem-" + hashlib.sha256(raw).hexdigest()[:24]
        ek = EffectKey(key, permission.permission_id, tool, fp, at)
        self._issued[slot] = ek
        return ek

    def issued(self) -> int:
        return len(self._issued)
