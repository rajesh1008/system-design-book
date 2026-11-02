"""Isolation: keep big things out of the lead agent's context.

Two moves. A tool result over a threshold goes to the run's artifact
store and the context gets a handle and a two-line digest; the agent
reads a slice back by handle when it needs one. Fare-rule research
with more than a few passages goes to a sub-agent with its own
context, read-only tools, and one job: return a cited digest. The
sub-agent cannot change anything, because it is never handed a tool
that can.
"""
from __future__ import annotations

from dataclasses import dataclass, field, replace

from common.rand import seeded

from .runs import Run, Step
from .slots import Item

ARTIFACT_OVER = 6_000      # tokens; above this a result is stored
SLICE_TOKENS = 800         # a slice read back by handle
READ_BACK = 0.4            # share of stored results read back once
DIGEST_TOKENS = 60         # handle plus two lines
RESEARCH_OVER = 1_200      # retrieved tokens a step before delegating
RESEARCH_DIGEST = 300      # the sub-agent's cited digest
SUBAGENT_OWN = 400         # the sub-agent's own instructions

READ_ONLY = frozenset({"fare_rules.search", "fare_rules.read",
                       "artifacts.read"})
EFFECT = frozenset({"refund.issue", "rebook.execute", "voucher.issue",
                    "approval.request"})


class NotPermitted(PermissionError):
    pass


@dataclass
class SubAgent:
    """A research worker. Its tool list is fixed at creation; asking
    for any other tool raises before anything is called."""
    name: str
    tools: frozenset = READ_ONLY
    calls: list[str] = field(default_factory=list)

    def __post_init__(self):
        bad = self.tools & EFFECT
        if bad:
            raise NotPermitted(f"{self.name} may not hold {sorted(bad)}")

    def use(self, tool: str) -> None:
        if tool not in self.tools:
            raise NotPermitted(f"{self.name} has no tool {tool}")
        self.calls.append(tool)


@dataclass
class ArtifactStore:
    items: dict = field(default_factory=dict)

    def put(self, run_id: str, step: int, text: str) -> str:
        handle = f"art://{run_id}/s{step}"
        self.items[handle] = text
        return handle

    def read(self, handle: str, start: int = 0, n: int = 5) -> str:
        lines = self.items[handle].splitlines()
        return "\n".join(lines[start:start + n])


@dataclass
class Isolated:
    run: Run
    to_store: int = 0          # tokens moved to the artifact store
    to_worker: int = 0         # retrieved tokens read by a sub-agent
    worker_calls: int = 0
    worker_tokens: int = 0     # what the sub-agent itself read
    read_back: int = 0         # slices read back by handle


def isolate(run: Run, store_over: int = ARTIFACT_OVER,
            research_over: int = RESEARCH_OVER) -> Isolated:
    out = Isolated(run)
    r = seeded(21, "isolate", run.run_id)
    steps = []
    owed = 0                   # slices to read back on the next step
    for s in run.steps:
        hist = []
        for j in range(owed):
            hist.append(Item("history", f"{run.run_id}:s{s.n}:slice{j}",
                             SLICE_TOKENS))
            out.read_back += 1
        owed = 0
        for it in s.history:
            if it.key.endswith(":tool") and it.tokens > store_over:
                out.to_store += it.tokens - DIGEST_TOKENS
                hist.append(Item("history", it.key + ":art",
                                 DIGEST_TOKENS))
                owed += r.random() < READ_BACK
            else:
                hist.append(it)
        ret = s.retrieved
        size = sum(i.tokens for i in ret)
        if size > research_over:
            out.to_worker += size - RESEARCH_DIGEST
            out.worker_calls += 1
            out.worker_tokens += size + SUBAGENT_OWN
            ret = [Item("retrieved", f"{run.run_id}:s{s.n}:digest",
                        RESEARCH_DIGEST)]
        steps.append(replace(s, history=hist, retrieved=ret))
    out.run = replace(run, steps=steps)
    return out
