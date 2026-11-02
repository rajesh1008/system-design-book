"""Two keys that decide who may reuse what.

`response_key` is the key for a cache of whole answers, which sits in
front of the model and returns a stored reply without calling it. It
names every input that could change the right answer: the tenant, the
policy version, the pinned model, the layout version, and the
normalized request. Leave one out and the cache serves a reply that
was right for someone else or for last week's rules.

`probe` replays the side channel a shared engine cache opens: a
caller who can guess a victim's prompt can time the first token and
learn whether the victim's text is already cached.
"""
from __future__ import annotations

import hashlib
import json

from .layout import stable_first
from .prefix import EngineCache
from .trace import Seg, Task

KEY_FIELDS = ("tenant", "policy", "model", "layout", "request")


def response_key(tenant: str, policy: str, model: str, layout: str,
                 request: dict) -> str:
    body = json.dumps({"tenant": tenant, "policy": policy,
                       "model": model, "layout": layout,
                       "request": request}, sort_keys=True,
                      separators=(",", ":"))
    return "rsp:" + hashlib.sha256(body.encode()).hexdigest()[:32]


def probe(victim: Task, guess: Seg, mode: str = "shared",
          prefill_tok_s: float = 11800) -> dict:
    """The victim's first call warms an engine cache; the attacker
    sends the same public prefix plus a guessed itinerary. Returns the
    tokens the attacker's call matched and the prefill time saved."""
    c = EngineCache(900000, 16)
    r = stable_first(victim, victim.calls[0])
    pub = next(i for i, s in enumerate(r.segs)
               if s.key == victim.itinerary.key)

    def salt_for(who: str) -> tuple[str, int]:
        if mode == "shared":
            return "", 0
        return who, (0 if mode == "traveler" else pub)

    c.call(r, 0.0, 0, *salt_for(victim.customer))
    a = stable_first(victim, victim.calls[0])
    a.segs[pub] = guess
    c.call(a, 1.0, 0, *salt_for("attacker"))
    m = c.last_matched
    public = sum(s.tokens for s in r.segs[:pub])
    return {"matched": m, "public": public,
            "leak": m > public,
            "saved_ms": 1000 * m / prefill_tok_s}
