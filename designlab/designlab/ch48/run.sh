#!/usr/bin/env bash
# Chapter 48 lab: the final scoreboard checked against itself; the four
# questions named for two shipped designs; the renaming cycle read
# against them; what runtimes have absorbed and what stays; mandates
# down a chain of agents that hire agents; Lakeshore's year-two plan
# (DR-48.1) and its pinned-model window; and the plan linter, clean and
# then with each fault injected. Offline; no model call and no key.
set -euo pipefail
cd "$(dirname "$0")/.."
PY=${PYTHON:-python3}
for part in card chain renames runtimes hire template plan window check; do
    "$PY" -m plan.demo --part "$part"
    echo
done
# Failure injection: each of these is expected to fail.
for fault in roadmap retired undated self-signed crowded; do
    "$PY" -m plan.demo --part check --fault "$fault" || true
    echo
done
"$PY" -m plan.demo --part hire --fault widen || true
echo
echo "== tests =="
DESIGNLAB_OFFLINE=1 "$PY" -m unittest plan.test_plan -v
