#!/usr/bin/env bash
# Chapter 35 lab: trace every step of a refund run, price every span,
# check completeness against the gateway trail, inject a tool call
# outside the trace, replay from the trace, alerts and sampling.
# Offline; no API key is used.
set -euo pipefail
cd "$(dirname "$0")/.."
PY=${PYTHON:-python3}
echo "== one run as spans =="
"$PY" -m tracing.demo --part spans
echo "== the June 9 gap: no policy span =="
"$PY" -m tracing.demo --part gap
echo "== cost on spans, cost per decision =="
"$PY" -m tracing.demo --part cost
echo "== completeness check =="
"$PY" -m tracing.demo --part complete
echo "== failure injection: a tool call outside the trace =="
"$PY" -m tracing.demo --part inject
echo "== strict replay from the trace =="
"$PY" -m tracing.demo --part replay
echo "== what-if replay: other harness and policy versions =="
"$PY" -m tracing.demo --part version
echo "== alerts that mean something =="
"$PY" -m tracing.demo --part alerts
echo "== sampling and the tail buffer =="
"$PY" -m tracing.demo --part sampling
echo "== observability card =="
"$PY" -m tracing.demo --part card
echo "== tests =="
DESIGNLAB_OFFLINE=1 "$PY" -m unittest tracing.test_tracing -v
