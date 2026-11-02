"""Chapter 19 live lab: the small model plans the queries and writes
the answer; code verifies, budgets and checks grounding.

Twelve desk tasks (ten answerable, two not) go through the same loop as
the demo. The model proposes each next query as JSON, seeing the
question, the slots the verifier still finds unmet and the queries it
already tried. The verifier and the budget are code. When the verifier
is satisfied, the model writes claims with a value and a citation,
seeing only the passages the verifier accepted. The grounding check
then compares each claim's value and citation with the passage.
Reads ANTHROPIC_API_KEY from the environment through common.client and
never prints it. About 30 short calls; the meter caps spend at $0.05.

    python3 -m retrieval.live
"""
from __future__ import annotations

import json
import re

from common.client import ModelClient
from common.spend import SpendMeter
from common.text import emit
from corpus.docs import CARRIERS, TOPICS

from . import agentic
from .tasks import RUNAWAY, tasks

LIVE_IDS = ("T01", "T02", "T03", "T04", "T05", "T06", "T08", "T09",
            "T10", "T11", "T15")

PLAN_SYSTEM = (
    "You search Lakeshore Travel Group's fare-rule and notice index "
    "for a servicing agent. Reply with JSON only: {\"query\": \"...\"} "
    "with one short search query aimed at the first missing item, or "
    "{\"stop\": true} if no query is likely to find it.")

ANSWER_SYSTEM = (
    "You answer a servicing agent's question using only the passages "
    "given. Reply with JSON only: {\"claims\": [{\"topic\": \"...\", "
    "\"value\": \"...\", \"cite\": \"<doc id>\"}]}, one claim per "
    "topic listed. The value is what the passage says for the fare "
    "product asked about, e.g. \"$75\", \"no fee\", \"not permitted\" "
    "or \"Basic included\". Cite the passage you took it from.")


def _json(text: str) -> dict:
    m = re.search(r"\{.*\}", text, re.S)
    try:
        return json.loads(m.group(0)) if m else {}
    except json.JSONDecodeError:
        return {}


def _slot_words(s) -> str:
    name = dict(CARRIERS)[s.carrier]
    if s.topic.startswith("waiver"):
        return f"{name} travel waiver for {s.topic[7:]}"
    return f"{name} {TOPICS[s.topic][0]} rule, {s.product} fare"


class ModelPlanner:
    def __init__(self, client: ModelClient):
        self.client = client
        self.bad = 0
        self.stops = 0
        self.cut = 0
        self.unparsed: list[str] = []

    def queries(self, task, gaps):
        yield task.question
        tried = [task.question]
        while True:
            missing = gaps() or list(task.slots)
            prompt = (f"Question: {task.question}\n"
                      f"Missing: {'; '.join(_slot_words(s) for s in missing)}"
                      f"\nAlready tried: {json.dumps(tried)}")
            # The model may think before it answers; a tight cap cuts
            # it off mid-thought with no text at all.
            r = self.client.complete(prompt, system=PLAN_SYSTEM,
                                     max_tokens=1024)
            self.cut += r.stop_reason == "max_tokens"
            out = _json(r.text)
            if not out.get("query"):
                if out.get("stop"):
                    self.stops += 1
                else:
                    self.bad += 1
                    self.unparsed.append(r.text[:200])
                return
            q = str(out["query"])[:200]
            if q in tried:
                return
            tried.append(q)
            yield q


def _value_ok(claim: dict, doc, product: str) -> bool:
    said = str(claim.get("value", "")).lower()
    if doc.kind == "notice":
        want = doc.facts.get("Basic", "")
        return ("basic" in said and want in said) or product != "Basic"
    v = doc.facts.get(product)
    if v is None:
        return "not" in said
    if v == "0":
        return "no " in said or "free" in said or "$0" in said
    return re.search(rf"\b{re.escape(v)}\b", said) is not None


def answer(client: ModelClient, task, run) -> list[tuple]:
    pool = [h.doc for h in run.evidence
            if any(agentic.admissible(h.doc, s, task.as_of)
                   for s in task.slots)]
    passages = "\n".join(f"[{d.doc_id}] {d.text}" for d in pool)
    topics = ", ".join(s.topic for s in task.slots)
    prompt = (f"Question: {task.question}\nTopics: {topics}\n"
              f"Passages:\n{passages}")
    r = client.complete(prompt, system=ANSWER_SYSTEM, max_tokens=1024)
    claims = _json(r.text).get("claims", [])
    ids = {d.doc_id: d for d in pool}
    out = []
    for s in task.slots:
        c = next((c for c in claims if c.get("topic") == s.topic), None)
        doc = ids.get(str((c or {}).get("cite")))
        if c is None or doc is None:
            out.append((s, "no valid citation"))
        elif not agentic.admissible(doc, s, task.as_of):
            out.append((s, "cites inadmissible"))
        elif not _value_ok(c, doc, s.product):
            out.append((s, f"value differs: {c.get('value')}"[:30]))
        else:
            out.append((s, "grounded"))
    return out


def run(client: ModelClient | None = None) -> list[str]:
    client = client or ModelClient("small",
                                   meter=SpendMeter(cap_usd=0.05))
    planner = ModelPlanner(client)
    chosen = [t for t in tasks() if t.tid in LIVE_IDS] + [RUNAWAY]
    lines, nq, verdicts, drift = [], [], [], 0
    for t in chosen:
        r = agentic.run(t, budget=8, planner=planner, cite="verified")
        nq.append(len(r.queries))
        v = answer(client, t, r) if r.stop == "verified" else []
        verdicts += [x for _, x in v]
        status = ("handed off" if not v
                  else ",".join(sorted(set(x for _, x in v))))
        lines.append(f"{t.tid} {'ans' if t.answerable else 'not'} "
                     f"q={len(r.queries)} {r.stop:9} {status}"[:70])
    nq.sort()
    good = verdicts.count("grounded")
    head = [f"tasks {len(chosen)} (answerable "
            f"{sum(t.answerable for t in chosen)}), budget 8",
            f"queries: median {nq[len(nq) // 2]}, max {nq[-1]}, "
            f"total {sum(nq)}",
            f"claims grounded {good} of {len(verdicts)}",
            f"planner stopped itself {planner.stops}, "
            f"cut off {planner.cut}, unparsed {planner.bad}"]
    tail = [f"model calls {client.meter.calls}, "
            f"spent ${client.meter.spent_usd:.4f}"]
    return head + lines + tail


if __name__ == "__main__":
    for line in run():
        emit(line)
