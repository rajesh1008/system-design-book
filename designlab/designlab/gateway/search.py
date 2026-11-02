"""Tool search: find the right definitions without loading them all.

The catalog is the registry, filtered to approved entries this caller
may use; nothing outside the registry can be found, so nothing outside
it can be loaded. Ranking is BM25 over the name and description.
Deferred loading means the model starts with the search tool and a few
always-loaded tools, and receives full definitions only for hits.
"""
from __future__ import annotations

import json
import math
import re
from collections import Counter

from .core import tokens_of

WORD = re.compile(r"[a-z0-9]+")
STOP = {"the", "a", "an", "of", "on", "or", "and", "to", "for", "by",
        "one", "in", "is", "its", "it", "this", "that", "with", "from",
        "be", "are", "may", "only", "not", "no"}

DOMAINS = {
    "hotel": ("room", "rate", "folio", "stay"),
    "car": ("rental", "vehicle", "pickup", "driver"),
    "loyalty": ("points", "tier", "member", "status"),
    "crm": ("contact", "account", "case", "note"),
    "erp": ("invoice", "ledger", "vendor", "purchase"),
    "itsm": ("incident", "problem", "ticket", "queue"),
    "hr": ("employee", "leave", "shift", "roster"),
    "finance": ("payment", "settlement", "chargeback", "payout"),
    "rail": ("train", "coach", "platform", "fare"),
    "visa": ("passport", "entry", "document", "country"),
}
VERBS = ("get", "list", "search", "update", "create", "cancel", "export",
         "check")
READS = ("get", "list", "search", "export", "check")
ALWAYS = ("booking_read", "flight_status", "handoff_to_desk")


def words(text: str) -> list[str]:
    return [w for w in WORD.findall(text.lower().replace("_", " "))
            if w not in STOP]


def synthetic(n: int, seed_words=DOMAINS) -> list[tuple[str, dict]]:
    """n made-up tools from ten domains, deterministic."""
    out = []
    i = 0
    doms = sorted(seed_words)
    while len(out) < n:
        d = doms[i % len(doms)]
        noun = seed_words[d][(i // len(doms)) % 4]
        verb = VERBS[(i // (len(doms) * 4)) % len(VERBS)]
        k = i // (len(doms) * 4 * len(VERBS))
        name = f"{d}_{verb}_{noun}" + (f"_{k}" if k else "")
        desc = (f"{verb.capitalize()} {d} {noun} records in the {d} "
                f"system. Returns {noun} fields for one request.")
        schema = {"type": "object", "properties": {
            f"{noun}_id": {"type": "string"}}, "required": [f"{noun}_id"],
            "additionalProperties": False}
        kind = "read" if verb in READS else "effect"
        out.append((f"{d}-tools", {"name": name, "description": desc,
                                   "version": "1.0", "kind": kind,
                                   "input_schema": schema}))
        i += 1
    return out


class ToolSearch:
    def __init__(self, registry, caller):
        self.entries = [e for e in registry.approved()
                        if e.tool in caller.tools]
        self.docs = [words(e.tool + " " + e.description)
                     for e in self.entries]
        self.df = Counter(w for d in self.docs for w in set(d))
        self.avg = sum(map(len, self.docs)) / max(1, len(self.docs))

    def search(self, query: str, k: int = 3) -> list[str]:
        n = len(self.docs)
        q = words(query)
        scored = []
        for e, d in zip(self.entries, self.docs):
            tf = Counter(d)
            s = 0.0
            for w in q:
                if w not in tf:
                    continue
                idf = math.log(1 + (n - self.df[w] + 0.5) /
                               (self.df[w] + 0.5))
                f = tf[w]
                s += idf * f * 2.2 / (f + 1.2 * (0.25 + 0.75 * len(d) /
                                                  self.avg))
            if s > 0:
                scored.append((-s, e.tool))
        return [t for _, t in sorted(scored)[:k]]

    def definition(self, tool: str) -> str:
        e = next(e for e in self.entries if e.tool == tool)
        return json.dumps({"name": e.tool, "description": e.description,
                           "input_schema": e.schema})

    def tokens_all(self) -> int:
        return sum(tokens_of(self.definition(e.tool))
                   for e in self.entries)

    def tokens_deferred(self, hits: list[str]) -> int:
        search_tool = tokens_of({"name": "tool_search", "description":
                                 "Find tools by what they do. Returns "
                                 "names; definitions load on use.",
                                 "input_schema": {"query": "string"}})
        keep = [t for t in ALWAYS if any(e.tool == t
                                         for e in self.entries)]
        return search_tool + sum(tokens_of(self.definition(t))
                                 for t in set(keep) | set(hits))


QUERIES = [
    ("how much of this ticket can be refunded", "fare_calc"),
    ("is the flight canceled or delayed", "flight_status"),
    ("find a replacement flight for a canceled segment",
     "offers_search"),
    ("read the carrier waiver notice", "notice_read"),
    ("refund part of a ticket", "refund_ticket"),
    ("move the passenger to a new flight reissue ticket",
     "rebook_ticket"),
    ("send the customer a message", "customer_notify"),
    ("give the case to a person at the desk", "handoff_to_desk"),
    ("read a document the customer uploaded", "doc_intake"),
    ("fare rule for a carrier fare product", "fare_rules_search"),
    ("issue a travel credit on the ticket", "credit_issue"),
    ("goodwill voucher within policy", "voucher_issue"),
]


def hit_rate(ts: ToolSearch, k: int = 3) -> tuple[int, int, list]:
    misses = []
    hits = 0
    for q, want in QUERIES:
        got = ts.search(q, k)
        if want in got:
            hits += 1
        else:
            misses.append((want, got))
    return hits, len(QUERIES), misses
