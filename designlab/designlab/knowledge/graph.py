"""An entity graph for itineraries, with bounded, typed traversal.

Nodes are travelers, itineraries, segments, tickets, flights, carriers,
cards, and corporate accounts. Edges are typed, and a traversal names
the edge types it may follow, a hop budget, and a fan-out cap; when
either stops it, the answer says "exploration incomplete" instead of
pretending to be whole. Authority is a separate question with its own
rule: it does not travel along edges. Sharing a flight, a surname, or
an itinerary as a companion grants nothing. The Okafor records are
Chapter 16's.
"""
from __future__ import annotations

from collections import deque
from dataclasses import dataclass, field

EDGE_TYPES = ("booked_by", "has_segment", "on_flight", "operated_by",
              "ticket_for", "covers", "card_on_file", "member_of",
              "arranger_of", "companion", "pays_with")


@dataclass
class Graph:
    kind: dict = field(default_factory=dict)        # node -> type
    out: dict = field(default_factory=dict)         # node -> [(etype, n)]
    inn: dict = field(default_factory=dict)

    def add(self, node: str, kind: str) -> None:
        self.kind[node] = kind
        self.out.setdefault(node, [])
        self.inn.setdefault(node, [])

    def link(self, a: str, etype: str, b: str) -> None:
        if etype not in EDGE_TYPES:
            raise ValueError(f"unknown edge type {etype}")
        self.out[a].append((etype, b))
        self.inn[b].append((etype, a))

    def edges(self) -> int:
        return sum(len(v) for v in self.out.values())


@dataclass
class Walk:
    found: list
    hops_used: int
    complete: bool
    stopped_by: str = ""
    visited: int = 0


def traverse(g: Graph, start: str, follow: list[tuple[str, str]],
             want: str, hop_budget: int = 4, fanout_cap: int = 50) -> Walk:
    """Breadth-first along `follow`, a list of (edge type, direction)
    steps applied in order, one step a hop. Returns nodes of type
    `want` and whether the walk was complete."""
    frontier, seen = [start], {start}
    found: list = []
    stopped = ""
    hops = 0
    for etype, direction in follow:
        if hops >= hop_budget:
            stopped = f"hop budget {hop_budget} reached"
            break
        hops += 1
        nxt = []
        for n in frontier:
            adj = g.out[n] if direction == "out" else g.inn[n]
            hits = [m for t, m in adj if t == etype and m not in seen]
            if len(hits) > fanout_cap:
                stopped = f"fan-out cap {fanout_cap} at {n}"
                hits = hits[:fanout_cap]
            for m in hits:
                seen.add(m)
                nxt.append(m)
        frontier = nxt
        found += [m for m in frontier if g.kind[m] == want]
    return Walk(sorted(set(found)), hops, not stopped, stopped, len(seen))


def path(g: Graph, a: str, b: str, max_hops: int = 4) -> list | None:
    """Shortest typed path from a to b in either direction, or None."""
    q, prev = deque([a]), {a: None}
    depth = {a: 0}
    while q:
        n = q.popleft()
        if n == b:
            break
        if depth[n] >= max_hops:
            continue
        for t, m in [(t, m) for t, m in g.out[n]] + \
                [(f"~{t}", m) for t, m in g.inn[n]]:
            if m not in prev:
                prev[m], depth[m] = (n, t), depth[n] + 1
                q.append(m)
    if b not in prev:
        return None
    out, n = [], b
    while prev[n] is not None:
        p, t = prev[n]
        out.append((p, t, n))
        n = p
    return out[::-1]


def may_act(g: Graph, actor: str, itinerary: str) -> tuple[bool, str]:
    """Authority to change an itinerary. Two grants only, never chained:
    the traveler who booked it, or an arranger of the account the
    booker belongs to. Nothing else along any edge counts."""
    bookers = [m for t, m in g.out[itinerary] if t == "booked_by"]
    if actor in bookers:
        return True, "booked it"
    for b in bookers:
        for t, acct in g.out[b]:
            if t == "member_of" and ("arranger_of", acct) in g.out[actor]:
                return True, f"arranger of {acct}"
    near = path(g, actor, itinerary, 6)
    how = " / ".join(t for _, t, _ in near) if near else "no path"
    return False, f"no grant (connected by: {how})"


def lakeshore_sample() -> Graph:
    """The Okafors' two bookings (Chapter 16), plus a small party, an
    arranger, and a canceled flight's neighborhood."""
    g = Graph()
    for n, k in [("Ngozi Okafor", "traveler"), ("Tunde Okafor", "traveler"),
                 ("LTG-5208841", "itinerary"), ("LTG-5208842", "itinerary"),
                 ("SEG-1", "segment"), ("SEG-2", "segment"),
                 ("TKT-40218", "ticket"), ("TKT-40219", "ticket"),
                 ("FLT-904417", "flight"), ("XMY", "carrier"),
                 ("ACCT-Tunde-employer", "account"),
                 ("Corporate arranger", "traveler"),
                 ("CARD-employer", "card")]:
        g.add(n, k)
    g.link("LTG-5208841", "booked_by", "Ngozi Okafor")
    g.link("LTG-5208842", "booked_by", "Tunde Okafor")
    g.link("LTG-5208841", "has_segment", "SEG-1")
    g.link("LTG-5208842", "has_segment", "SEG-2")
    g.link("SEG-1", "on_flight", "FLT-904417")
    g.link("SEG-2", "on_flight", "FLT-904417")
    g.link("FLT-904417", "operated_by", "XMY")
    g.link("TKT-40218", "ticket_for", "Ngozi Okafor")
    g.link("TKT-40218", "covers", "SEG-1")
    g.link("TKT-40219", "ticket_for", "Tunde Okafor")
    g.link("TKT-40219", "covers", "SEG-2")
    g.link("Tunde Okafor", "member_of", "ACCT-Tunde-employer")
    g.link("Corporate arranger", "arranger_of", "ACCT-Tunde-employer")
    g.link("LTG-5208842", "pays_with", "CARD-employer")
    # A busy flight: 180 more itineraries on FLT-904417, one a party.
    for i in range(180):
        it, tr, sg = f"LTG-53{i:05d}", f"Traveler {i}", f"SEG-X{i}"
        g.add(it, "itinerary"); g.add(tr, "traveler"); g.add(sg, "segment")
        g.link(it, "booked_by", tr)
        g.link(it, "has_segment", sg)
        g.link(sg, "on_flight", "FLT-904417")
    g.add("Party friend", "traveler")
    g.link("LTG-5300000", "companion", "Party friend")
    return g
