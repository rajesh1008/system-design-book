"""The Model Contract: the interface a model call site promises.

A contract is a TOML file in `models/contracts/`. It names the step, the
owner, the pinned model and what kind of ID that pin is, the dates by
which the pin must be reviewed, the input limits, the output schema (with
extra fields rejected and some fields forbidden outright), what counts as
a refusal, and the latency and cost bounds. `check` applies all of it to
one completion and returns every violation, never just the first.

Money never comes from a model. A contract lists the money-shaped field
names it forbids, and a desk-facing contract also forbids money-shaped
text, so an amount cannot slip in as prose.
"""
from __future__ import annotations

import hashlib
import json
import re
import tomllib
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path

CONTRACT_DIR = Path(__file__).with_name("contracts")
ID_KINDS = ("snapshot", "alias")
TYPES = ("enum", "string", "boolean")


@dataclass(frozen=True)
class OutputField:
    name: str
    type: str
    values: tuple[str, ...] = ()
    pattern: str | None = None
    max_len: int | None = None
    max_words: int | None = None
    nullable: bool = False
    quote_of: str | None = None     # must be copied from this input


@dataclass(frozen=True)
class Violation:
    code: str
    detail: str

    def __str__(self) -> str:
        return f"{self.code}: {self.detail}"


@dataclass(frozen=True)
class ModelContract:
    name: str
    version: str
    owner: str
    alert_to: str
    step: str
    role: str
    model_id: str
    id_kind: str
    expect_echo: str
    retire_not_before: date
    review_by: date
    max_input_chars: int
    max_tokens: int
    sampling: str
    p95_latency_s: float
    max_cost_usd: float
    on_violation: str
    system: str
    template: str
    golden: str
    fields: tuple[OutputField, ...]
    extra_fields: str = "reject"
    forbidden_fields: tuple[str, ...] = ()
    forbidden_text: str | None = None
    refusal_codes: tuple[str, ...] = ()
    decoding: str = "free"          # or "constrained" (provider schema)

    def json_schema(self) -> dict:
        """The output schema in the provider's JSON Schema subset. Length
        and word limits are not expressible there, so `check` keeps them."""
        props = {}
        for f in self.fields:
            p: dict = {"type": "boolean" if f.type == "boolean"
                       else "string"}
            if f.values:
                p["enum"] = list(f.values)
            if f.pattern:
                p["pattern"] = f.pattern
            if f.nullable:
                p = {"anyOf": [p, {"type": "null"}]}
            props[f.name] = p
        return {"type": "object", "properties": props,
                "required": list(self.field_names()),
                "additionalProperties": False}

    @property
    def prompt_hash(self) -> str:
        raw = json.dumps([self.system, self.template, self.decoding],
                         sort_keys=True)
        return hashlib.sha256(raw.encode()).hexdigest()[:12]

    def render(self, inputs: dict) -> str:
        return self.template.format(**inputs)

    def field_names(self) -> tuple[str, ...]:
        return tuple(f.name for f in self.fields)

    def days_to_review(self, today: date) -> int:
        return (self.review_by - today).days


def _field(d: dict) -> OutputField:
    if d["type"] not in TYPES:
        raise ValueError(f"field {d['name']}: unknown type {d['type']}")
    return OutputField(name=d["name"], type=d["type"],
                       values=tuple(d.get("values", ())),
                       pattern=d.get("pattern"), max_len=d.get("max_len"),
                       max_words=d.get("max_words"),
                       nullable=d.get("nullable", False),
                       quote_of=d.get("quote_of"))


def load_contract(path: Path) -> ModelContract:
    with Path(path).open("rb") as f:
        d = tomllib.load(f)
    if d["id_kind"] not in ID_KINDS:
        raise ValueError(f"{path}: id_kind must be one of {ID_KINDS}")
    out = d["output"]
    c = ModelContract(
        name=d["name"], version=d["version"], owner=d["owner"],
        alert_to=d["alert_to"], step=d["step"], role=d["role"],
        model_id=d["model_id"], id_kind=d["id_kind"],
        expect_echo=d["expect_echo"],
        retire_not_before=date.fromisoformat(d["retire_not_before"]),
        review_by=date.fromisoformat(d["review_by"]),
        max_input_chars=d["max_input_chars"], max_tokens=d["max_tokens"],
        sampling=d["sampling"], p95_latency_s=d["p95_latency_s"],
        max_cost_usd=d["max_cost_usd"], on_violation=d["on_violation"],
        system=d["system"].strip(), template=d["template"].strip(),
        golden=d["golden"],
        fields=tuple(_field(x) for x in out["fields"]),
        extra_fields=out.get("extra_fields", "reject"),
        forbidden_fields=tuple(out.get("forbidden_fields", ())),
        forbidden_text=out.get("forbidden_text"),
        refusal_codes=tuple(out.get("refusal_codes", ())),
        decoding=d.get("decoding", "free"))
    if c.decoding not in ("free", "constrained"):
        raise ValueError(f"{c.name}: decoding must be free or constrained")
    if c.review_by >= c.retire_not_before:
        raise ValueError(f"{c.name}: review_by must come before retirement")
    return c


def load_contracts(directory: Path = CONTRACT_DIR) -> dict[str, ModelContract]:
    return {c.name: c for c in (load_contract(p)
                                for p in sorted(directory.glob("*.toml")))}


def parse_json(text: str) -> dict | None:
    """The object in the text, allowing one fenced block; None if none."""
    t = text.strip()
    m = re.fullmatch(r"```(?:json)?\s*(.*?)\s*```", t, re.S)
    if m:
        t = m.group(1)
    try:
        obj = json.loads(t)
    except ValueError:
        return None
    return obj if isinstance(obj, dict) else None


def _norm(s: str) -> str:
    return " ".join(s.lower().split())


def check_output(c: ModelContract, obj: dict | None,
                 inputs: dict | None = None) -> list[Violation]:
    if obj is None:
        return [Violation("not-json", "output is not one JSON object")]
    v: list[Violation] = []
    names = c.field_names()
    for k in obj:
        if k in c.forbidden_fields:
            v.append(Violation("forbidden-field", k))
        elif k not in names and c.extra_fields == "reject":
            v.append(Violation("extra-field", k))
    for f in c.fields:
        if f.name not in obj:
            v.append(Violation("missing-field", f.name))
            continue
        val = obj[f.name]
        if val is None:
            if not f.nullable:
                v.append(Violation("null", f.name))
            continue
        if f.type == "boolean":
            if not isinstance(val, bool):
                v.append(Violation("bad-type", f"{f.name} not boolean"))
            continue
        if not isinstance(val, str):
            v.append(Violation("bad-type", f"{f.name} not a string"))
            continue
        if f.type == "enum" and val not in f.values:
            v.append(Violation("bad-enum", f"{f.name}={val!r}"))
        if f.pattern and not re.fullmatch(f.pattern, val):
            v.append(Violation("bad-pattern", f"{f.name}={val!r}"))
        if f.max_len is not None and len(val) > f.max_len:
            v.append(Violation("too-long", f"{f.name} {len(val)} chars"))
        if f.max_words is not None and len(val.split()) > f.max_words:
            v.append(Violation("too-long",
                               f"{f.name} {len(val.split())} words"))
        if f.quote_of and inputs is not None:
            if _norm(val) not in _norm(str(inputs.get(f.quote_of, ""))):
                v.append(Violation("not-quoted", f"{f.name} not in input"))
        if c.forbidden_text and re.search(c.forbidden_text, val):
            v.append(Violation("forbidden-text", f"{f.name} has money"))
    return v


def check(c: ModelContract, completion, inputs: dict | None = None,
          latency_s: float | None = None) -> list[Violation]:
    """Every way one completion breaks its contract."""
    v: list[Violation] = []
    if completion.model != c.expect_echo:
        v.append(Violation("echo-drift",
                           f"asked {c.model_id}, got {completion.model}"))
    if completion.stop_reason == "max_tokens":
        v.append(Violation("truncated", f"hit max_tokens={c.max_tokens}"))
    if completion.stop_reason == "refusal":
        v.append(Violation("refusal", "provider refused"))
    if latency_s is not None and latency_s > c.p95_latency_s:
        v.append(Violation("slow", f"{latency_s:.1f} s > "
                                   f"{c.p95_latency_s:.1f} s"))
    if completion.cost_usd > c.max_cost_usd:
        v.append(Violation("dear", f"${completion.cost_usd:.5f}"))
    if completion.stop_reason != "refusal":
        v += check_output(c, parse_json(completion.text), inputs)
    return v


def check_input(c: ModelContract, inputs: dict) -> list[Violation]:
    n = len(c.render(inputs))
    if n > c.max_input_chars:
        return [Violation("input-too-long", f"{n} > {c.max_input_chars}")]
    return []
