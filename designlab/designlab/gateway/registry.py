"""The registry: what may be called, who reviewed it, and its hash.

An entry is one tool on one server at one version. It is submitted
with its description, input schema, kind, scopes and owner. The
screen flags what a reviewer must look at; a person decides. An
approved entry stores the SHA-256 of the name, description and schema
the reviewer read, and the gateway compares that hash with what the
server serves on every call. A changed description is a new
submission, not an update.
"""
from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass, field

SUBMITTED, APPROVED, REJECTED = "submitted", "approved", "rejected"

# Phrases that address the model rather than describe the tool.
INSTRUCTION = [
    re.compile(r"\balways (include|send|pass|attach|add)\b", re.I),
    re.compile(r"\b(ignore|disregard) (previous|other|prior)\b", re.I),
    re.compile(r"\bbefore (calling|using) any other tool\b", re.I),
    re.compile(r"\bdo not (tell|mention|show)\b", re.I),
    re.compile(r"\b(full|entire|whole) (booking|record|profile)\b",
               re.I),
]
FREE_TEXT_NAMES = re.compile(r"(profile|record|context|notes|metadata"
                             r"|payload|extra)", re.I)
KNOWN_SCOPES = {"read": {"case:read"}, "effect": {"case:effect"},
                "handoff": {"case:read"}}


def description_hash(name: str, description: str, schema: dict) -> str:
    raw = json.dumps({"name": name, "description": description,
                      "input_schema": schema}, sort_keys=True,
                     separators=(",", ":"))
    return hashlib.sha256(raw.encode()).hexdigest()


@dataclass
class Entry:
    server: str
    tool: str
    version: str
    kind: str
    description: str
    schema: dict
    scopes: tuple[str, ...]
    owner: str
    status: str = SUBMITTED
    desc_hash: str = ""
    reviewer: str = ""
    reviewed_at: str = ""
    findings: list[str] = field(default_factory=list)


def screen(e: Entry) -> list[str]:
    """What the reviewer must look at. Not a verdict."""
    out = []
    for rx in INSTRUCTION:
        m = rx.search(e.description)
        if m:
            out.append(f"instruction to the model: '{m.group(0)}'")
            break
    for name, sub in e.schema.get("properties", {}).items():
        free = (sub.get("type") == "string" and "pattern" not in sub
                and "enum" not in sub)
        if free and FREE_TEXT_NAMES.search(name):
            out.append(f"free-text field '{name}' can carry anything")
    extra = set(e.scopes) - KNOWN_SCOPES.get(e.kind, set())
    if extra:
        out.append(f"scopes beyond a {e.kind} tool: "
                   f"{', '.join(sorted(extra))}")
    if e.kind == "read" and re.search(r"\b(update|write|change|set)\b",
                                       e.description, re.I):
        out.append("a read tool whose description says it writes")
    if not e.owner:
        out.append("no owner")
    return out


class Registry:
    def __init__(self, trail, clock):
        self.trail = trail
        self.clock = clock
        self.entries: dict[tuple[str, str], Entry] = {}
        self.history: list[Entry] = []

    def submit(self, server, spec: dict, scopes, owner: str) -> Entry:
        e = Entry(server=server, tool=spec["name"],
                  version=spec["version"], kind=spec["kind"],
                  description=spec["description"],
                  schema=spec["input_schema"], scopes=tuple(scopes),
                  owner=owner)
        e.findings = screen(e)
        self.entries[(server, e.tool)] = e
        self.trail.append({"event": "registry_submit", "server": server,
                           "tool": e.tool, "version": e.version,
                           "findings": len(e.findings)})
        return e

    def review(self, server: str, tool: str, reviewer: str,
               approve: bool, note: str = "") -> Entry:
        """A person decides. Approval with open findings is refused."""
        e = self.entries[(server, tool)]
        if approve and e.findings:
            raise ValueError(f"{tool}: findings open: {e.findings[0]}")
        e.status = APPROVED if approve else REJECTED
        e.reviewer = reviewer
        e.reviewed_at = self.clock.now().isoformat()
        e.desc_hash = description_hash(e.tool, e.description, e.schema) \
            if approve else ""
        self.history.append(e)
        self.trail.append({"event": "registry_review", "server": server,
                           "tool": tool, "status": e.status,
                           "reviewer": reviewer, "note": note,
                           "hash": e.desc_hash[:12]})
        return e

    def lookup(self, server: str, tool: str) -> Entry | None:
        return self.entries.get((server, tool))

    def approved(self) -> list[Entry]:
        return [e for e in self.entries.values() if e.status == APPROVED]

    def rejected(self) -> list[Entry]:
        return [e for e in self.entries.values() if e.status == REJECTED]

    def check_served(self, server, tool: str, served: dict) -> bool:
        e = self.lookup(server, tool)
        if e is None or e.status != APPROVED:
            return False
        return description_hash(tool, served["description"],
                                served["input_schema"]) == e.desc_hash
