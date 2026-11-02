#!/usr/bin/env bash
# Chapter 12 lab: the refund failure at scale, injected and fixed.
# The fall-1 corpus (April 14, 2026), the batch path with a key per
# attempt, the alert, settlement, the fixed path, the breaker, and the
# Try It variations. Offline; no model call and no key needed.
set -euo pipefail
cd "$(dirname "$0")/.."
PY=${PYTHON:-python3}

echo "== the afternoon, injected and fixed =="
"$PY" -m failure.demo
echo
echo "== try it: key per attempt, with and without the guard =="
"$PY" -m failure.demo --part tryit --mint attempt
echo
echo "== try it: trip the breaker at other latencies =="
"$PY" -m failure.demo --part tryit --slow-s 3
echo
echo "== try it: reconcile every 5 and every 60 minutes =="
"$PY" -m failure.demo --part tryit --every 15
echo
echo "== tests =="
DESIGNLAB_OFFLINE=1 "$PY" -m unittest corpus.test_fall1 \
  effects.test_guard failure.test_failure -v
