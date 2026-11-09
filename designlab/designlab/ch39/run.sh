#!/usr/bin/env bash
# Chapter 39 lab: the release bundle, the release log, regression as a
# gate, the what-if over last week's runs, canaries by task type,
# rollback with runs in flight, a memory schema rolled back, shadow,
# a fixed-horizon A/B and the cost of peeking, a bandit on approvals,
# the deploy step, and the change card. Offline; no model call and no
# key.
set -euo pipefail
cd "$(dirname "$0")/.."
PY=${PYTHON:-python3}
for part in bundle log gate whatif canary rollback memory shadow ab \
            bandit deploy card; do
    "$PY" -m release.demo --part "$part"
    echo
done
"$PY" -m release.demo --part gate --alone
echo
"$PY" -m release.demo --part whatif --steps 12
echo
"$PY" -m release.demo --part canary --task rebooking
echo
echo "== tests =="
DESIGNLAB_OFFLINE=1 "$PY" -m unittest release.test_release -v
