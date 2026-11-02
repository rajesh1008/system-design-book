"""Variance: how far one input's output moves between identical calls.

Fixture replay cannot show this (one request hash, one recorded answer),
so live sampling writes every sample into one JSON file under
`fixtures/`, and the offline demo summarizes that file. A sample keeps
the text, the echoed model, and the stop reason; never a header.

Three questions, each answered from samples:
  decisions  do the fields a downstream step acts on change?
  text       does the wording change (usually yes, and usually fine)?
  contract   does the output still satisfy the contract every time?
"""
from __future__ import annotations

import json
from collections import Counter
from dataclasses import dataclass
from pathlib import Path

from common.redact import redact
from common.spend import SpendMeter

from .contract import ModelContract, check, parse_json
from .runner import client_for


def collect(c: ModelContract, cases: list[dict], n: int, transport,
            meter: SpendMeter, temperature: float | None = None,
            out: list[dict] | None = None) -> list[dict]:
    """Appends to `out` as it goes, so a spend cap keeps what was paid."""
    cl = client_for(c, transport, meter)          # no cache, no record
    out = [] if out is None else out
    for case in cases:
        prompt = c.render(case["input"])
        for i in range(n):
            comp = cl.complete(prompt, system=c.system,
                               max_tokens=c.max_tokens,
                               temperature=temperature)
            out.append({"case": case["id"], "i": i, "text": comp.text,
                        "model": comp.model, "stop": comp.stop_reason,
                        "cost_usd": round(comp.cost_usd, 8)})
    return out


def save(path: Path, meta: dict, samples: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(redact({"meta": meta, "samples": samples}),
                               indent=1, sort_keys=True) + "\n")


def load(path: Path) -> tuple[dict, list[dict]]:
    d = json.loads(path.read_text())
    return d["meta"], d["samples"]


@dataclass
class CaseSpread:
    case: str
    n: int
    texts: int                  # distinct raw outputs
    decisions: Counter          # distinct decision tuples
    contract_ok: int

    @property
    def top_share(self) -> float:
        return self.decisions.most_common(1)[0][1] / self.n


class _Done:
    """Stands in for a Completion when re-checking a stored sample."""

    def __init__(self, s: dict):
        self.text, self.model = s["text"], s["model"]
        self.stop_reason, self.cost_usd = s["stop"], 0.0


def spread(c: ModelContract, samples: list[dict], keys: tuple[str, ...],
           inputs: dict[str, dict] | None = None) -> list[CaseSpread]:
    by: dict[str, list[dict]] = {}
    for s in samples:
        by.setdefault(s["case"], []).append(s)
    rows = []
    for case, ss in by.items():
        dec = Counter()
        ok = 0
        for s in ss:
            obj = parse_json(s["text"]) or {}
            dec[tuple(obj.get(k) for k in keys)] += 1
            inp = (inputs or {}).get(case)
            ok += not check(c, _Done(s), inp)
        rows.append(CaseSpread(case, len(ss), len({s["text"] for s in ss}),
                               dec, ok))
    return rows
