#!/usr/bin/env bash
# Chapter 2 labs. Offline by default. Set ANTHROPIC_API_KEY for
# the live step: two short calls to the small model, under a cent.
set -euo pipefail
cd "$(dirname "$0")/.."
PY=${PYTHON:-python3}
"$PY" -m chain.demo
"$PY" -m chain.incident
"$PY" -m chain.lab --gaps
if [ -n "${ANTHROPIC_API_KEY:-}" ]; then "$PY" -m chain.live; fi
DESIGNLAB_OFFLINE=1 "$PY" -m unittest chain.test_chain \
  chain.test_states chain.test_check
