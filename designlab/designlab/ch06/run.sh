#!/usr/bin/env bash
# Chapter 6 lab: four planes, six contracts, the path test, and the
# autonomy table. Offline; seed 6; no model call and no key needed.
set -euo pipefail
cd "$(dirname "$0")/.."
PY=${PYTHON:-python3}

echo "== the reference wiring =="
"$PY" -m planes.demo --seed 6
echo
echo "== the same week with the injected fast path =="
"$PY" -m planes.demo --seed 6 --bypass --part replay
"$PY" -m planes.demo --seed 6 --bypass --part paths
echo
echo "== tests =="
DESIGNLAB_OFFLINE=1 "$PY" -m unittest planes.test_planes -v
