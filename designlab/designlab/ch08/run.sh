#!/usr/bin/env bash
# Chapter 8 lab: the asynchronous spine. Ordering per itinerary,
# backpressure on approvals, dead letters, and the fan-out of one
# airline cancellation. Offline; seed 8; no model call and no key.
set -euo pipefail
cd "$(dirname "$0")/.."
PY=${PYTHON:-python3}

echo "== the spine, seed 8 =="
"$PY" -m spine.demo --seed 8
echo
echo "== the same storm with half the desk =="
"$PY" -m spine.demo --seed 8 --part desk --reviewers 3
echo
echo "== tests =="
DESIGNLAB_OFFLINE=1 "$PY" -m unittest spine.test_spine -v
