"""The names a span must carry, by kind.

Source: open-telemetry/semantic-conventions-genai, read 2026-11-02.
Every GenAI attribute there has status Development, the repository
has no release, and its schema URL is still marked TODO, so Lakeshore
pins the names here and maps them in one place. When the conventions
rename something, this file changes and nothing else does.

The conventions define no cost, policy or verification attributes;
those live under `lakeshore.*`.
"""
from __future__ import annotations

PINNED = "semantic-conventions-genai, Development, read 2026-11-02"

OP = "gen_ai.operation.name"
PROVIDER = "gen_ai.provider.name"
AGENT_NAME = "gen_ai.agent.name"
AGENT_VERSION = "gen_ai.agent.version"
CONVERSATION = "gen_ai.conversation.id"
MODEL = "gen_ai.request.model"
IN_TOKENS = "gen_ai.usage.input_tokens"
OUT_TOKENS = "gen_ai.usage.output_tokens"
CACHE_READ = "gen_ai.usage.cache_read.input_tokens"
FINISH = "gen_ai.response.finish_reasons"
TOOL_NAME = "gen_ai.tool.name"
TOOL_CALL = "gen_ai.tool.call.id"
TOOL_TYPE = "gen_ai.tool.type"

COST = "lakeshore.cost.usd"
DECISION_COST = "lakeshore.decision.cost_usd"
STEP = "lakeshore.step"
HARNESS_HASH = "lakeshore.harness.hash"
OUTCOME = "lakeshore.outcome"
STEPS = "lakeshore.steps"
TOOL_KIND = "lakeshore.tool.kind"
VERDICT = "lakeshore.gateway.verdict"
ARGS_DIGEST = "lakeshore.args.sha256"
IO_REF = "lakeshore.io.ref"
POLICY = "lakeshore.policy.id"
POLICY_VERDICT = "lakeshore.policy.verdict"
PERMIT = "lakeshore.permit.id"
AMOUNT = "lakeshore.amount.usd"
TRAIL = "lakeshore.trail.hash"
VERIFY_RESULT = "lakeshore.verify.result"
VERIFY_BY = "lakeshore.verify.by"
VERIFY_OF = "lakeshore.verify.of"

REQUIRED = {
    "invoke_agent": (OP, PROVIDER, AGENT_NAME, AGENT_VERSION,
                     CONVERSATION, HARNESS_HASH),
    "chat": (OP, PROVIDER, MODEL, IN_TOKENS, OUT_TOKENS, COST),
    "execute_tool": (OP, TOOL_NAME, TOOL_CALL, TOOL_TYPE, VERDICT, COST),
    "step": (STEP,),
    "policy": (POLICY, POLICY_VERDICT, AMOUNT),
    "verify": (VERIFY_RESULT, VERIFY_BY, VERIFY_OF),
}


def kind_of(name: str) -> str:
    head = name.split(" ", 1)[0]
    if head in ("invoke_agent", "chat", "execute_tool", "step"):
        return head
    if head.startswith("policy"):
        return "policy"
    if head.startswith("verify"):
        return "verify"
    return "unknown"


def agent_name(agent: str) -> str:
    return f"invoke_agent {agent}"


def chat_name(model: str) -> str:
    return f"chat {model}"


def tool_name(tool: str) -> str:
    return f"execute_tool {tool}"


def check_span(span) -> list[str]:
    """Problems with one span's names; empty when it conforms."""
    k = kind_of(span.name)
    if k == "unknown":
        return [f"{span.name}: no convention and no lakeshore kind"]
    out = [f"{span.name}: missing {a}" for a in REQUIRED[k]
           if a not in span.attrs]
    if k in ("invoke_agent", "chat", "execute_tool"):
        if span.attrs.get(OP) != k:
            out.append(f"{span.name}: {OP} is {span.attrs.get(OP)}")
    if k == "chat" and span.name != chat_name(span.attrs.get(MODEL)):
        out.append(f"{span.name}: name does not match model")
    return out
