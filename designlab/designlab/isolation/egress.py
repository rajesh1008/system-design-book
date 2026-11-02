"""Egress as policy: an allow-list of hosts by tool, deny by default.

Every outbound request from a session passes `EgressPolicy.check`,
which parses the URL the way the proxy will, normalizes the host, and
allows it only when the tool is listed for that host and port. IP
literals are refused outright, because an address is where a name
pointed once, not who answers there now. Every denial writes one line
to the trail with the tool, the host, and the reason. Redirects are
checked hop by hop through `follow`.
"""
from __future__ import annotations

import ipaddress
import tomllib
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urlsplit

from common.trail import TrailWriter

HERE = Path(__file__).resolve().parent


@dataclass(frozen=True)
class Verdict:
    allowed: bool
    tool: str
    host: str
    reason: str


def load_policy(path: Path | None = None) -> dict:
    with open(path or HERE / "egress.toml", "rb") as f:
        return tomllib.load(f)


def _norm(host: str | None) -> str:
    return (host or "").strip().rstrip(".").lower()


class EgressPolicy:
    def __init__(self, policy: dict | None = None, trail=None,
                 clock=None):
        self.policy = policy or load_policy()
        self.trail = trail or TrailWriter(clock=clock)
        self.hosts: dict[tuple[str, int], set[str]] = {}
        for h in self.policy["host"]:
            key = (_norm(h["name"]), int(h.get("port", 443)))
            self.hosts.setdefault(key, set()).update(h["tools"])
        self.allowed = 0
        self.allowed_hosts: dict[str, int] = {}
        self.denied = 0

    @property
    def owner(self) -> str:
        return self.policy.get("owner", "")

    def host_count(self) -> int:
        return len({name for name, _ in self.hosts})

    def check(self, tool: str, url: str, session: str = "") -> Verdict:
        try:
            parts = urlsplit(url)
            host = _norm(parts.hostname)
            port = parts.port or {"https": 443, "http": 80}.get(
                parts.scheme, -1)
        except ValueError:
            return self._deny(tool, url[:40], "unparseable url", session)
        if parts.scheme != "https":
            return self._deny(tool, host, f"scheme {parts.scheme}",
                              session)
        try:
            ipaddress.ip_address(host)
            return self._deny(tool, host, "ip literal", session)
        except ValueError:
            pass
        tools = self.hosts.get((host, port))
        if tools is None:
            return self._deny(tool, host, "host not listed", session)
        if tool not in tools:
            return self._deny(tool, host, "tool not listed for host",
                              session)
        self.allowed += 1
        self.allowed_hosts[host] = self.allowed_hosts.get(host, 0) + 1
        return Verdict(True, tool, host, "listed")

    def follow(self, tool: str, hops: list[str],
               session: str = "") -> Verdict:
        """Check a redirect chain; the first refused hop stops it."""
        v = Verdict(False, tool, "", "no hops")
        for url in hops:
            v = self.check(tool, url, session)
            if not v.allowed:
                return v
        return v

    def _deny(self, tool, host, reason, session) -> Verdict:
        self.denied += 1
        self.trail.append({"kind": "egress_denied", "tool": tool,
                           "host": host, "reason": reason,
                           "session": session})
        return Verdict(False, tool, host, reason)
