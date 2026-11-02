"""The trail checker: what can the trail answer about every effect?

For each request that reached the world, the checker asks four
questions of the trail alone, without the executor's word:

    allowed    is there a permission line, before the effect, from a
               component other than the one that acted
    policy     does that line name a policy version
    once       is there a key, so a retry can be told from a new action
    verified   did a component that did not act find exactly one effect

It also re-derives the hash links, so an edited or deleted line shows.
"""
from __future__ import annotations

import json
from collections import defaultdict

from common.trail import check_trail

from .v0 import ACTOR

QUESTIONS = ("allowed", "policy", "once", "verified")
EFFECT_EVENTS = ("execution", "tool_call")


def audit(lines: list[str]) -> dict:
    by_req: dict[str, list[dict]] = defaultdict(list)
    for line in lines:
        e = json.loads(line)
        by_req[e.get("req", "?")].append(e)
    out = {"requests": len(by_req), "answers": 0, "denied": 0,
           "refused": 0, "acted": 0, "verified_ok": 0,
           "duplicates_seen": 0,
           "unanswered": {q: 0 for q in QUESTIONS},
           "links": check_trail(lines)}
    for events in by_req.values():
        kinds = [e["event"] for e in events]
        if kinds == ["output"] and events[0].get("class") == "answer":
            out["answers"] += 1
        out["denied"] += kinds.count("denied")
        out["refused"] += kinds.count("refused")
        first_effect = next((i for i, k in enumerate(kinds)
                             if k in EFFECT_EVENTS), None)
        if first_effect is None:
            continue
        out["acted"] += 1
        before = events[:first_effect]
        perm = next((e for e in before if e["event"] == "permission"
                     and e.get("by") != ACTOR), None)
        ver = next((e for e in events if e["event"] == "verification"
                    and e.get("verified_by") != ACTOR), None)
        answered = {
            "allowed": perm is not None,
            "policy": perm is not None and bool(perm.get("policy")),
            "once": perm is not None and bool(perm.get("key")),
            "verified": ver is not None and ver.get("ok") is True,
        }
        for q, ok in answered.items():
            if not ok:
                out["unanswered"][q] += 1
        if ver is not None and ver.get("ok"):
            out["verified_ok"] += 1
        if ver is not None and ver.get("found", 0) > 1:
            out["duplicates_seen"] += 1
    return out
