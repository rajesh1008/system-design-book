"""Versioned policy bundles and their life cycle.

A bundle is data: an ordered list of rules, each with a type and its
parameters, plus the policy versions the rules belong to. Its digest
is computed over that data, so the decision log can name exactly the
rules that decided. A bundle moves draft, shadow, active, then
superseded; any state may be revoked. Only one bundle is active at a
time, and a revoked policy version voids every permission it granted
that has not been spent.
"""
from __future__ import annotations

import copy
import hashlib
import json
from dataclasses import dataclass, field

STATES = ("draft", "shadow", "active", "superseded", "revoked")
MOVES = {"draft": ("shadow", "revoked"),
         "shadow": ("active", "draft", "revoked"),
         "active": ("superseded", "revoked"),
         "superseded": (), "revoked": ()}


class BundleError(Exception):
    pass


@dataclass
class Bundle:
    revision: str
    rules: list[dict]
    author: str
    state: str = "draft"
    signed_by: str = ""
    history: list[tuple[str, str, str]] = field(default_factory=list)

    @property
    def digest(self) -> str:
        blob = json.dumps(self.rules, sort_keys=True).encode()
        return hashlib.sha256(blob).hexdigest()[:12]

    def versions(self) -> list[str]:
        return sorted({r["policy"] for r in self.rules})

    def rule(self, rule_id: str) -> dict:
        return next(r for r in self.rules if r["id"] == rule_id)


class BundleStore:
    """Holds every bundle ever proposed. Never deletes one."""

    def __init__(self, clock):
        self.clock = clock
        self.bundles: dict[str, Bundle] = {}
        self.revoked_versions: set[str] = set()

    def propose(self, revision: str, rules: list[dict],
                author: str) -> Bundle:
        if revision in self.bundles:
            raise BundleError(f"{revision} exists; bundles are immutable")
        b = Bundle(revision, copy.deepcopy(rules), author)
        b.history.append((self._now(), "draft", author))
        self.bundles[revision] = b
        return b

    def move(self, revision: str, to: str, who: str) -> Bundle:
        b = self.bundles[revision]
        if to not in MOVES[b.state]:
            raise BundleError(f"{revision}: {b.state} to {to} refused")
        if to == "active":
            if not b.signed_by or b.signed_by == b.author:
                raise BundleError(f"{revision}: needs a signer who is "
                                  "not the author")
            for other in self.bundles.values():
                if other.state == "active":
                    other.state = "superseded"
                    other.history.append((self._now(), "superseded",
                                          who))
        b.state = to
        b.history.append((self._now(), to, who))
        return b

    def sign(self, revision: str, signer: str) -> None:
        b = self.bundles[revision]
        if signer == b.author:
            raise BundleError(f"{revision}: the author cannot sign it")
        b.signed_by = signer

    def active(self) -> Bundle | None:
        return next((b for b in self.bundles.values()
                     if b.state == "active"), None)

    def shadow(self) -> Bundle | None:
        return next((b for b in self.bundles.values()
                     if b.state == "shadow"), None)

    def revoke_version(self, policy_version: str, who: str) -> None:
        """Every unspent permission granted under this version is void
        from now on. The rules stay readable for the record."""
        self.revoked_versions.add(policy_version)
        for b in self.bundles.values():
            if policy_version in b.versions():
                b.history.append((self._now(),
                                  f"version {policy_version} revoked",
                                  who))

    def _now(self) -> str:
        return self.clock.now().isoformat(timespec="seconds")
