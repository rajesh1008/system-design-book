#!/usr/bin/env bash
# Chapter 24 lab: the stale memory, injected and fixed. Offline; no key
# needed. The live check replays recorded fixtures unless --record.
set -euo pipefail
cd "$(dirname "$0")/.."
PY=${PYTHON:-python3}
echo "== the fall and the fix, seed 2026 =="
"$PY" -m knowops.demo
echo
echo "== failure injection: no destination verifier =="
"$PY" -m knowops.demo --no-verifier
echo
echo "== try it: a destination memory with a 365-day TTL =="
"$PY" -m knowops.demo --ttl 365
echo
echo "== the weekly fresh sample against the golden set =="
"$PY" -m knowops.demo --weekly
echo
echo "== failure injection: an index frozen on May 4 =="
"$PY" -m knowops.demo --weekly --age-index
echo
echo "== the pinned note against the record (replayed) =="
"$PY" -m knowops.live
echo
echo "== tests =="
DESIGNLAB_OFFLINE=1 "$PY" -m unittest corpus.test_fall2 \
    knowops.test_knowops knowops.test_live -v
