"""The evidence pack: an auditor's questions about a period, answered
from the trail, with the records that answer them, and sealed.

Chapter 35 made one refund answerable: Rachel Morgan's eleven questions
from one trace. An auditor asks about a period. Which refunds, under
which releases and rules, approved by whom, sent where, confirmed how,
and what went wrong. The pack answers each period question with a
count, its exceptions, and the trail sequence numbers that support it.
It draws a seeded sample of complete chains, each with an inclusion
proof to that day's anchored root, and seals the whole with a manifest
of hashes. The pack is generated, never written by hand, so the same
trail and the same seed give the same pack, byte for byte.

LAB_SEAL is a lab stand-in for a signing key held outside engineering.
It is public, in this file, on purpose: the lab shows the mechanics of
a seal, not a secret.
"""
from __future__ import annotations

import hashlib
import hmac
import json
from collections import Counter

from common.rand import seeded
from common.trail import check_trail, line_hash

from . import anchor

LAB_SEAL = b"lab-seal-not-a-secret"
LINKS = ("proposal", "decision", "approval", "execution", "verified",
         "notice")
QUESTIONS = (
    ("P1", "Which refunds did the agent path issue, and for how much?"),
    ("P2", "Which release handled each run?"),
    ("P3", "Which signed rules decided each proposal?"),
    ("P4", "Did a person approve the exact arguments that executed?"),
    ("P5", "Did every refund go to a form of payment that paid?"),
    ("P6", "Did the ledger confirm every refund?"),
    ("P7", "Which proposals were rejected or handed off, and why?"),
    ("P8", "What changed during the period?"),
    ("P9", "Which findings opened, and are they closed?"),
    ("P10", "Was every customer told they were dealing with AI?"),
    ("P11", "Is the trail complete, and does it match the anchors?"),
)


def _runs(entries: list[dict]) -> dict[str, dict]:
    runs: dict[str, dict] = {}
    for e in entries:
        if "run" in e:
            runs.setdefault(e["run"], {})[e["event"]] = e
    return runs


def answer(lines: list[str], held: dict[str, str]) -> dict[str, dict]:
    entries = [json.loads(x) for x in lines]
    runs = _runs(entries)
    out: dict[str, dict] = {}
    ex = [r for r in runs.values() if "execution" in r]
    total = sum(float(r["verified"]["amount_usd"]) for r in ex
                if "verified" in r)
    out["P1"] = {"count": len(ex), "amount_usd": f"{total:,.2f}",
                 "exceptions": [],
                 "evidence": [r["execution"]["seq"] for r in ex]}
    rel = Counter(r["run"]["release"] for r in runs.values())
    out["P2"] = {"count": len(runs), "by": dict(sorted(rel.items())),
                 "exceptions": [], "evidence": "run lines"}
    dec = [r for r in runs.values() if "decision" in r]
    unsigned = [r["decision"]["seq"] for r in dec
                if not r["decision"].get("signed_by")]
    bund = Counter(r["decision"]["bundle"] for r in dec)
    out["P3"] = {"count": len(dec), "by": dict(sorted(bund.items())),
                 "exceptions": unsigned, "evidence": "decision lines"}
    unbound = [r["execution"]["seq"] for r in ex
               if r.get("approval", {}).get("args")
               != r["execution"]["args"]]
    edited = sum(1 for r in ex if r["approval"]["verdict"] == "edited")
    out["P4"] = {"count": len(ex), "edited": edited,
                 "exceptions": unbound, "evidence": "approval lines"}
    wrong = [r["execution"]["seq"] for r in ex
             if not set(r["execution"]["refund_to"])
             <= set(r["run"]["forms_paid"])]
    proposed = [r["proposal"]["proposal"] for r in runs.values()
                if "proposal" in r and r["proposal"]["refund_to"]
                not in r["run"]["forms_paid"]]
    out["P5"] = {"count": len(ex), "exceptions": wrong,
                 "proposed_elsewhere": proposed,
                 "evidence": "execution lines"}
    unver = [r["execution"]["seq"] for r in ex
             if r.get("verified", {}).get("ledger") != "match"]
    out["P6"] = {"count": len(ex), "exceptions": unver,
                 "evidence": "verified lines"}
    rej = [{"run": k, "why": r["approval"]["why"]}
           for k, r in runs.items()
           if r.get("approval", {}).get("verdict") == "rejected"]
    hand = sum(1 for r in runs.values() if "handoff" in r)
    out["P7"] = {"rejected": rej, "handoffs": hand,
                 "exceptions": [], "evidence": "approval, handoff"}
    ch = [f'{e["at"][:10]} {e["kind"]}: {e["what"]}' for e in entries
          if e["event"] == "change"]
    out["P8"] = {"count": len(ch), "changes": ch, "exceptions": [],
                 "evidence": "change lines"}
    fnd = [c for c in ch if " finding: " in c]
    out["P9"] = {"count": len(fnd), "findings": fnd,
                 "exceptions": [], "evidence": "finding record"}
    unseen = [r["run"]["seq"] for r in runs.values()
              if r["run"].get("ai_notice") != "shown"]
    out["P10"] = {"count": len(runs), "exceptions": unseen,
                  "evidence": "run lines"}
    out["P11"] = {"lines": len(lines), "chain": check_trail(lines),
                  "anchors": anchor.check(lines, held),
                  "exceptions": [], "evidence": "anchors held by audit"}
    out["P11"]["exceptions"] = out["P11"]["chain"] + out["P11"]["anchors"]
    return out


def sample(lines: list[str], seed: str, n: int = 60) -> list[dict]:
    """n executed refunds, drawn by the auditor's seed, each checked as a
    complete chain and proven against its day's root."""
    entries = [json.loads(x) for x in lines]
    runs = _runs(entries)
    pool = sorted(k for k, r in runs.items() if "execution" in r)
    picked = sorted(seeded(0, seed).sample(pool, n))
    days = anchor.by_day(lines)
    out = []
    for k in picked:
        r = runs[k]
        missing = [x for x in LINKS if x not in r]
        bound = r.get("approval", {}).get("args") == \
            r.get("execution", {}).get("args")
        dest = set(r["execution"]["refund_to"]) <= \
            set(r["run"]["forms_paid"])
        proofs = [anchor.prove(lines, r[x]["seq"] - 1, days)
                  for x in ("run",) + LINKS if x in r]
        out.append({"run": k, "missing": missing, "bound": bound,
                    "destination_paid": dest, "proofs": proofs})
    return out


def check_sample(item: dict, held: dict[str, str]) -> list[str]:
    bad = [f"no {x}" for x in item["missing"]]
    if not item["bound"]:
        bad.append("approval not bound to execution")
    if not item["destination_paid"]:
        bad.append("destination did not pay")
    for p in item["proofs"]:
        if not anchor.verify(p["leaf"], p["path"], held.get(p["day"])):
            bad.append(f"proof fails for {p['day']}")
    return bad


def _digest(obj) -> str:
    raw = json.dumps(obj, sort_keys=True).encode()
    return hashlib.sha256(raw).hexdigest()


def generate(lines: list[str], held: dict[str, str], period: str,
             seed: str, n: int = 60, admissible: dict | None = None,
             seal: bytes = LAB_SEAL) -> dict:
    body = {
        "period": period,
        "trail": {"lines": len(lines),
                  "first": line_hash(lines[0]),
                  "last": line_hash(lines[-1])},
        "anchors": held,
        "questions": dict(QUESTIONS),
        "answers": answer(lines, held),
        "sample": {"seed": seed, "items": sample(lines, seed, n)},
        "admissibility": admissible or {},
    }
    manifest = {k: _digest(v) for k, v in body.items()}
    pack_digest = _digest(manifest)
    body["manifest"] = manifest
    body["digest"] = pack_digest
    body["seal"] = hmac.new(seal, pack_digest.encode(),
                            hashlib.sha256).hexdigest()
    return body


def verify(pack: dict, held: dict[str, str],
           seal: bytes = LAB_SEAL) -> list[str]:
    """What an auditor runs: the seal, the manifest, the anchors they
    hold themselves, and every sampled chain's proofs."""
    bad = []
    parts = {k: v for k, v in pack.items()
             if k not in ("manifest", "digest", "seal")}
    for k, v in parts.items():
        if pack["manifest"].get(k) != _digest(v):
            bad.append(f"manifest: {k} changed")
    if _digest(pack["manifest"]) != pack["digest"]:
        bad.append("digest does not match manifest")
    want = hmac.new(seal, pack["digest"].encode(),
                    hashlib.sha256).hexdigest()
    if not hmac.compare_digest(want, pack["seal"]):
        bad.append("seal does not verify")
    if pack["anchors"] != held:
        bad.append("anchors differ from the ones audit holds")
    for item in pack["sample"]["items"]:
        for b in check_sample(item, held):
            bad.append(f'{item["run"]}: {b}')
    return bad
