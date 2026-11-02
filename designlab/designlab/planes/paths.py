"""The path test: no route from the agent loop to a system of record that
skips the gateway.

Two checks. `unmediated_paths` searches the declared wiring (static).
`probe_tools` calls every tool the loop holds with a record that has a
proposal and nothing else, in a scratch world, and reports any tool that
still produces an effect (dynamic). The static check finds wiring you
declared; the probe finds wiring you forgot to declare.
"""
from __future__ import annotations

import copy

from chain.record import ChainRecord, Proposal, Refused

from .action import GatewayTool

SYSTEMS = ("processor", "airline", "vouchers")


def wiring(loop) -> list[tuple[str, str]]:
    edges = [("agent-loop", "knowledge"), ("agent-loop", "control"),
             ("control", "trail"), ("gateway", "control"),
             ("gateway", "trail"), ("trail", "processor"),
             ("trail", "airline"), ("trail", "vouchers")]
    for name, tool in loop.tools.items():
        node = f"tool:{name}"
        if isinstance(tool, GatewayTool):
            edges += [("agent-loop", "gateway"), ("gateway", node)]
        else:
            edges.append(("agent-loop", node))
        edges.append((node, getattr(tool, "system", "unknown-system")))
    return sorted(set(edges))


def unmediated_paths(edges, start: str = "agent-loop") -> list[list[str]]:
    graph: dict[str, list[str]] = {}
    for a, b in edges:
        graph.setdefault(a, []).append(b)
    found = []

    def walk(node, path):
        for nxt in sorted(graph.get(node, [])):
            if nxt in path:
                continue
            p = path + [nxt]
            # Reads by the verifier are not effects; skip the trail plane.
            if nxt == "trail":
                continue
            if nxt in SYSTEMS or nxt == "unknown-system":
                if "gateway" not in p:
                    found.append(p)
            else:
                walk(nxt, p)

    walk(start, [start])
    return found


def probe_tools(loop, world) -> list[str]:
    flagged = []
    for name, tool in sorted(loop.tools.items()):
        scratch = copy.deepcopy(world)
        probe = copy.copy(tool)
        if isinstance(probe, GatewayTool):
            probe.gateway = copy.copy(tool.gateway)
            probe.gateway.world = scratch
        else:
            probe.world = scratch
        before = len(scratch.effects)
        record = ChainRecord(proposal=Proposal(
            "refund" if "refund" in name else name, "PROBE-0", 1.0,
            "path probe"))
        try:
            probe(record)
        except Refused:
            pass
        if len(scratch.effects) > before:
            flagged.append(name)
    return flagged
