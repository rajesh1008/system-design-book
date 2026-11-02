"""Question to metric query, through the metric-query Model Contract.

`to_query` asks the model for a metric query, checks the reply against
the contract, and turns it into a `MetricQuery`. `to_sql` is the shadow
trial's path, kept so the lab can show what raw SQL from the same model
looks like to the guard. Responses are cached in knowledge/fixtures, so
offline runs replay them.
"""
from __future__ import annotations

import os
import re
from dataclasses import dataclass
from datetime import date
from pathlib import Path

from common.client import FixtureTransport, ModelClient
from common.spend import SpendMeter
from models.contract import check, load_contract, parse_json

from . import layer as L
from .warehouse import CATALOG

HERE = Path(__file__).parent
FIXTURES = HERE / "fixtures"
CONTRACT = load_contract(HERE / "contracts" / "metric-query.toml")
TODAY_TEXT = "Wednesday, May 27, 2026"
RAW_SYSTEM = """You write one SQLite SELECT statement that answers a
Lakeshore Travel Group operations question from the warehouse schema
below. Timestamps are ISO 8601 text in UTC. Reply with the SQL only."""


def offline() -> bool:
    return os.environ.get("DESIGNLAB_OFFLINE") == "1" or \
        not os.environ.get("ANTHROPIC_API_KEY", "").strip()


def client(meter: SpendMeter, replay: bool | None = None) -> ModelClient:
    replay = offline() if replay is None else replay
    if replay:
        return ModelClient(CONTRACT.role, meter=meter,
                           transport=FixtureTransport(FIXTURES))
    return ModelClient(CONTRACT.role, meter=meter, cache_dir=FIXTURES)


@dataclass
class Translation:
    status: str                  # ok, not_in_layer, clarify, violation
    query: L.MetricQuery | None
    assumption: str
    violations: list
    cost_usd: float
    cached: bool
    model: str


def to_query(question: str, layer: L.Layer, c: ModelClient) -> Translation:
    inputs = {"today": TODAY_TEXT, "catalog": layer.catalog_text(),
              "question": question}
    r = c.complete(CONTRACT.render(inputs), system=CONTRACT.system,
                   max_tokens=CONTRACT.max_tokens)
    v = [str(x) for x in check(CONTRACT, r, inputs) if x.code != "slow"]
    obj = parse_json(r.text) or {}
    if v:
        return Translation("violation", None, "", v, r.cost_usd, r.cached,
                           r.model)
    status = obj["status"]
    q = None
    if status == "ok" and not (obj["start"] and obj["end"]):
        return Translation("violation", None, "", ["ok without a window"],
                           r.cost_usd, r.cached, r.model)
    if status == "ok":
        dims = tuple(d.strip() for d in obj["dimensions"].split(",")
                     if d.strip())
        filt = tuple(tuple(p.strip().split("=", 1))
                     for p in obj["filters"].split(";") if p.strip())
        q = L.MetricQuery(obj["metric"], date.fromisoformat(obj["start"]),
                          date.fromisoformat(obj["end"]), dims,
                          obj["grain"], filt)
    return Translation(status, q, obj.get("assumption", ""), [],
                       r.cost_usd, r.cached, r.model)


def schema_text() -> str:
    return "\n".join(f"{t.name}({', '.join(t.columns)})"
                     for t in CATALOG.values())


def to_sql(question: str, c: ModelClient) -> tuple[str, float, bool]:
    prompt = (f"Today is {TODAY_TEXT}.\nSchema:\n{schema_text()}\n\n"
              f"Question: {question}")
    r = c.complete(prompt, system=RAW_SYSTEM, max_tokens=1500)
    sql = r.text.strip()
    m = re.search(r"```(?:sql)?\s*(.*?)(?:```|$)", sql, re.S)
    if m:
        sql = m.group(1).strip()
    return sql.rstrip(";"), r.cost_usd, r.cached
