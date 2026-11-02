#!/usr/bin/env bash
# Chapter 21 lab: the context assembler, the budget from the rot curve,
# compaction policies, the summary verifier, isolation, and instruction
# drift. Offline; seed 21. The live samples replay from
# context/fixtures/live and models/fixtures/compaction; set
# ANTHROPIC_API_KEY and run "python3 -m context.live --record" and
# "python3 -m models.compaction --record" to record them anew.
set -euo pipefail
cd "$(dirname "$0")/.."
PY=${PYTHON:-python3}
export DESIGNLAB_OFFLINE=1

echo "== the lab, seed 21 =="
"$PY" -m context.demo --seed 21
echo
echo "== the injected unnoticed breach =="
"$PY" -m context.demo --seed 21 --inject unnoticed || echo "(exit $?)"
echo
echo "== the live samples, replayed =="
"$PY" -m context.live
"$PY" -m models.compaction
echo
echo "== Try It Yourself =="
"$PY" -m context.demo --seed 21 --part card --compact-at 0.5
"$PY" -m context.demo --seed 21 --part card --compact-at 0.9
"$PY" -m context.demo --seed 21 --part assemble --retrieved-first
"$PY" -m context.demo --seed 21 --part compact --lengths
echo
echo "== tests =="
"$PY" -m unittest context.test_context -v
