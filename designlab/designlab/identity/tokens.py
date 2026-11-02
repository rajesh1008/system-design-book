"""Run tokens: signed, short-lived, bound to one customer and one trip.

A token carries three identities: the customer it acts for (sub), the
agent configuration acting (act), and the run (run). It names one
itinerary, the tools the run may call, an audience, and an expiry.
The control plane signs it; anything that accepts it checks the
signature, the audience, the expiry, and the revocation list. The
signing key here is a lab constant, not a secret.
"""
from __future__ import annotations

import base64
import hashlib
import hmac
import json
from dataclasses import dataclass, field

LAB_KEY = hashlib.sha256(b"designlab identity lab, not a secret").digest()
AUDIENCE = "gateway.lakeshore.internal"
RUN_TTL_S = 900          # 15 minutes: no longer than the permission
ISSUER = "control-plane"


def _b64(raw: bytes) -> str:
    return base64.urlsafe_b64encode(raw).decode().rstrip("=")


def _unb64(text: str) -> bytes:
    return base64.urlsafe_b64decode(text + "=" * (-len(text) % 4))


def sign(body: bytes, key: bytes = LAB_KEY) -> str:
    return _b64(hmac.new(key, body, hashlib.sha256).digest())


@dataclass
class Claims:
    sub: str                 # the customer the run acts for
    act: str                 # the agent configuration acting
    run: str                 # this run
    itinerary: str           # the one trip the run may touch
    tools: tuple[str, ...]   # what the run may call
    iat: float
    exp: float
    jti: str
    aud: str = AUDIENCE
    iss: str = ISSUER

    def as_dict(self) -> dict:
        return {"iss": self.iss, "aud": self.aud, "sub": self.sub,
                "act": {"sub": self.act}, "run": self.run,
                "itinerary": self.itinerary, "tools": list(self.tools),
                "iat": self.iat, "exp": self.exp, "jti": self.jti}

    @classmethod
    def from_dict(cls, d: dict) -> "Claims":
        act = d.get("act") or {}
        return cls(sub=d["sub"], act=act.get("sub", ""), run=d["run"],
                   itinerary=d["itinerary"], tools=tuple(d["tools"]),
                   iat=d["iat"], exp=d["exp"], jti=d["jti"],
                   aud=d["aud"], iss=d["iss"])


def encode(claims: Claims, key: bytes = LAB_KEY) -> str:
    body = json.dumps(claims.as_dict(), sort_keys=True).encode()
    return f"{_b64(body)}.{sign(body, key)}"


@dataclass
class Verdict:
    """A refused token whose signature held still names who it was,
    so the refusal line in the trail can carry three identities."""
    ok: bool
    reason: str = ""
    claims: Claims | None = None


@dataclass
class Verifier:
    """What the gateway runs on every token it is shown."""
    revoked: set = field(default_factory=set)
    key: bytes = LAB_KEY
    audience: str = AUDIENCE

    def check(self, token: str, now: float) -> Verdict:
        try:
            body_b64, sig = token.split(".")
            body = _unb64(body_b64)
        except (ValueError, TypeError):
            return Verdict(False, "not_a_run_token")
        if not hmac.compare_digest(sig, sign(body, self.key)):
            return Verdict(False, "bad_signature")
        d = json.loads(body)
        if "run" not in d or "act" not in d:
            return Verdict(False, "not_a_run_token")
        c = Claims.from_dict(d)
        if c.aud != self.audience:
            return Verdict(False, "wrong_audience", claims=c)
        if now >= c.exp:
            return Verdict(False, "expired", claims=c)
        if c.jti in self.revoked or c.run in self.revoked:
            return Verdict(False, "revoked", claims=c)
        return Verdict(True, claims=c)
