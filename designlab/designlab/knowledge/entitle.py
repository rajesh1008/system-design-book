"""Entitlements that travel with the question.

The caller's entitlement comes from the session token the console was
given at sign-in, never from the question text and never from the
service account the warehouse sees. The layer checks it on every
query: the metric, each dimension, and a desk row filter for
desk-scoped metrics. Raw SQL is checked table by table and column by
column. The token here is signed with a lab-only salt; production signs
with the identity provider's key.
"""
from __future__ import annotations

import base64
import hashlib
import hmac
import json
from dataclasses import dataclass

from .warehouse import CATALOG

LAB_SALT = b"designlab-ch20-lab-only-not-a-secret"
DOMAIN_NEEDS = {"ops": ("ops", "finance", "risk"), "events": ("ops",),
                "finance": ("finance",), "pii": ("risk",)}
COLUMN_NEEDS = {"customer_id": ("risk",), "approver_id": ("hr",),
                "amount_usd": ("finance", "risk"),
                "cost_usd": ("finance",), "model_usd": ("finance",),
                "gross_usd": ("finance",)}


@dataclass(frozen=True)
class Entitlement:
    subject: str
    roles: tuple
    desks: tuple = ()             # empty: every desk
    token_id: str = ""

    def has_any(self, roles) -> bool:
        return any(r in self.roles for r in roles)


def issue(subject: str, roles, desks=(), token_id: str = "") -> str:
    body = json.dumps({"sub": subject, "roles": list(roles),
                       "desks": list(desks), "tid": token_id},
                      sort_keys=True).encode()
    sig = hmac.new(LAB_SALT, body, hashlib.sha256).hexdigest()[:24]
    return base64.urlsafe_b64encode(body).decode() + "." + sig


class BadToken(ValueError):
    pass


def from_token(token: str) -> Entitlement:
    """The only way an Entitlement is made outside tests."""
    try:
        b64, sig = token.rsplit(".", 1)
        body = base64.urlsafe_b64decode(b64.encode())
    except ValueError as e:
        raise BadToken("malformed token") from e
    want = hmac.new(LAB_SALT, body, hashlib.sha256).hexdigest()[:24]
    if not hmac.compare_digest(sig, want):
        raise BadToken("signature does not match")
    d = json.loads(body)
    return Entitlement(d["sub"], tuple(d["roles"]), tuple(d["desks"]),
                       d["tid"])


def check_metric(layer, metric, dims, filters, ent: Entitlement) -> list:
    """Reasons this caller may not ask this (empty when allowed)."""
    out = []
    if not ent.has_any(metric.entitle):
        out.append(f"{metric.name} needs {' or '.join(metric.entitle)}")
    for d in list(dims) + [k for k, _ in filters]:
        needs = layer.dimensions.get(d, ())
        if needs and not ent.has_any(needs):
            out.append(f"dimension {d} needs {' or '.join(needs)}")
    return out


def check_reads(reads: dict, ent: Entitlement) -> list:
    """For raw SQL: every table and column the statement reads."""
    out = []
    for table, cols in sorted(reads.items()):
        t = CATALOG.get(table)
        if t is None:
            out.append(f"{table} is not in the catalog")
            continue
        needs = DOMAIN_NEEDS[t.domain]
        if not ent.has_any(needs):
            out.append(f"{table} needs {' or '.join(needs)}")
        for c in sorted(cols):
            n = COLUMN_NEEDS.get(c)
            if n and not ent.has_any(n) and t.domain != "finance":
                out.append(f"{table}.{c} needs {' or '.join(n)}")
    return out


def desk_filter(metric, ent: Entitlement) -> tuple:
    return ent.desks if metric.desk_scoped else ()
