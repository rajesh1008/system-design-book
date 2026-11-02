"""designlab.trace: observability for one agent run (Chapter 35).

Spans for the run, its steps, model calls, tool calls, policy decisions
and verifications, named under the OpenTelemetry GenAI semantic
conventions where a convention exists and under `lakeshore.*` where
none does (cost, policy, verification, the chain link). Cost on every
span and per decision, a completeness check against the gateway trail,
replay from the exported trace with a diff against production, alert
rules, and tail-sampling arithmetic.

The package is named `trace`, so inside `04-code/designlab` it shadows
the standard library module of the same name. Nothing in designlab
uses the standard library one.
"""
from .spans import Span, Tracer
from .conventions import check_span

__all__ = ["Span", "Tracer", "check_span"]
