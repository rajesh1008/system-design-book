"""The release bundle: six kinds of change, one hash.

The June registry hashed the harness manifest. A prompt contract, a
policy bundle, a model behind an alias, or a memory schema could change
what the agent did while that hash stayed the same. The bundle hashes
all six, and the trail records the bundle hash on every run, so a run
can be tied to exactly one release, and a running configuration that
matches no released bundle is an unbundled change.
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field, replace

from harness import manifest as M

KINDS = ("prompt", "model", "tool", "harness", "policy", "memory")
STAGES = ("candidate", "gate", "shadow", "ab", "canary", "full",
          "rolled_back", "superseded")


def digest(text: str) -> str:
    return hashlib.sha256(text.encode()).hexdigest()[:12]


# Prompt texts by contract and version. The prompt part of a bundle
# holds their digests, so an edit of one character is a new bundle.
PROMPTS = {
    "refund-reason@1.3": "Classify the traveler's stated reason for a "
    "refund into one code from the list. If two codes fit, answer "
    "AMBIGUOUS. Do not infer intent the traveler did not state.",
    "desk-note@2.1": "Write the note a desk agent reads first: the "
    "booking, the request, the amounts from fare_calc, and the open "
    "question. No more than five lines.",
    "change-intent@1.0": "Classify the change the carrier made to the "
    "itinerary into one code from the list.",
    "notice@6": "Tell the traveler what changed, what we did, and what "
    "happens next, in that order, in plain words.",
}


def harness_hash(name: str) -> str:
    return M.short(M.manifest_hash(M.resolve(M.load(name))))


@dataclass(frozen=True)
class Bundle:
    """What one release ships. `parts` is hashed; the stage history and
    the signatures are recorded beside it and are not."""
    prompt: tuple[tuple[str, str], ...]      # (contract@version, digest)
    model: tuple[tuple[str, str], ...]       # (role, alias#snapshot)
    tool: tuple[tuple[str, str], ...]        # (server, build)
    harness: tuple[str, str]                 # (manifest, short hash)
    policy: str                              # policy bundle id
    memory: tuple[tuple[str, str], ...]      # (store, schema@version)

    def parts(self) -> dict:
        return {"prompt": dict(self.prompt), "model": dict(self.model),
                "tool": dict(self.tool),
                "harness": {"manifest": self.harness[0],
                            "hash": self.harness[1]},
                "policy": self.policy, "memory": dict(self.memory)}

    @property
    def hash(self) -> str:
        text = json.dumps(self.parts(), sort_keys=True,
                          separators=(",", ":"))
        return hashlib.sha256(text.encode()).hexdigest()[:12]

    def changed(self, other: "Bundle") -> list[str]:
        """The kinds of change between two bundles, in KINDS order."""
        a, b = self.parts(), other.parts()
        return [k for k in KINDS if a[k] != b[k]]

    def detail(self, other: "Bundle") -> list[str]:
        """One line per changed entry: kind.name old -> new."""
        a, b = self.parts(), other.parts()
        out = []
        for k in KINDS:
            x, y = a[k], b[k]
            if x == y:
                continue
            if not isinstance(x, dict):
                out.append(f"{k}: {x} -> {y}")
                continue
            for n in sorted(set(x) | set(y)):
                if x.get(n) != y.get(n):
                    out.append(f"{k}.{n}: {x.get(n, '-')} -> "
                               f"{y.get(n, '-')}")
        return out

    def with_prompt(self, name: str, text: str) -> "Bundle":
        p = dict(self.prompt)
        p[name] = digest(text)
        return replace(self, prompt=tuple(sorted(p.items())))

    def with_part(self, kind: str, name: str, value: str) -> "Bundle":
        if kind in ("policy",):
            return replace(self, policy=value)
        if kind == "harness":
            return replace(self, harness=(name, value))
        d = dict(getattr(self, kind))
        d[name] = value
        return replace(self, **{kind: tuple(sorted(d.items()))})


def base() -> Bundle:
    """The bundle running on Monday, July 13, 2026: harness 1.0.0, the
    classifier pinned to its June snapshot since July 8, pb-2026.06.22,
    and memory schema v2 under memory-retention-v2."""
    return Bundle(
        prompt=tuple(sorted((k, digest(v)) for k, v in PROMPTS.items())),
        model=(("frontier", "claude-opus-5-5#2026-05"),
               ("mid", "claude-sonnet-5-5#2026-05"),
               ("small", "claude-haiku-5-5#2026-06")),
        tool=(("payments", "3.0+b41"), ("rebook", "2.1+b17"),
              ("credits", "1.2+b09"), ("offers", "1.3+b22"),
              ("registry", "2026-06-19")),
        harness=("servicing-1.0.0", harness_hash("servicing-1.0.0")),
        policy="pb-2026.06.22.2",
        memory=(("fare_rules", "extract@2026-06"),
                ("traveler", "schema@2;retention@2")),
    )


@dataclass
class Record:
    """A bundle as the release log keeps it."""
    rid: str
    date: str
    bundle: Bundle
    parent: str                      # hash of the bundle it replaces
    kinds: list[str]
    owner: str
    signed: str = ""
    stages: list[tuple[str, str]] = field(default_factory=list)

    @property
    def stage(self) -> str:
        return self.stages[-1][1] if self.stages else "candidate"

    def move(self, when: str, stage: str) -> None:
        if stage not in STAGES:
            raise ValueError(f"unknown stage {stage}")
        self.stages.append((when, stage))


def trail_line(run_id: str, b: Bundle, stage: str) -> dict:
    """What the trail records about the release on every run."""
    return {"run": run_id, "bundle": b.hash, "stage": stage,
            "harness": b.harness[1], "policy": b.policy,
            "model": dict(b.model)}


def unbundled(observed: list[dict], released: set[str]) -> list[dict]:
    """Runs whose configuration, rebuilt from what they echoed, hashes
    to no released bundle."""
    return [o for o in observed if o["bundle"] not in released]
