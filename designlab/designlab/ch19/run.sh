#!/usr/bin/env bash
# Chapter 19: retrieval architecture and the bounded research loop.
# Offline. The live lab is separate: python3 -m retrieval.live needs
# ANTHROPIC_API_KEY in the environment and costs well under one cent.
set -euo pipefail
cd "$(dirname "$0")/.."
PY=${PYTHON:-python3}

echo "== the May 4 question: pilot stack and full pipeline =="
"$PY" -m retrieval.demo --case opening
echo
echo "== what a hit carries =="
"$PY" -m retrieval.demo --case provenance
echo
echo "== the golden set, configuration by configuration =="
"$PY" -m retrieval.demo --case golden
echo
echo "== one research loop, traced =="
"$PY" -m retrieval.demo --case loop
echo
echo "== forty desk tasks, budget 8 =="
"$PY" -m retrieval.demo --case loops
echo
echo "== grounding by budget =="
"$PY" -m retrieval.demo --case budgets
echo
echo "== without the reranker, citing whatever was read =="
"$PY" -m retrieval.demo --case loops --no-rerank --cite read
echo
echo "== inject: no-stop (verifier and budget removed) =="
"$PY" -m retrieval.demo --case loops --inject no-stop
echo
echo "== offline tests =="
DESIGNLAB_OFFLINE=1 "$PY" -m unittest retrieval.test_retrieval -v
echo
echo "== the budget test under inject (expected to fail) =="
RETRIEVAL_INJECT=no-stop DESIGNLAB_OFFLINE=1 \
  "$PY" -m unittest retrieval.test_retrieval.TestBudget \
  || echo "expected: the budget test fails without the stop rule"
