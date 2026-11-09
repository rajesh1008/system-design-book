#!/usr/bin/env bash
# Chapter 46 lab: the ladder as a timed drill. Seven levels and twelve
# prompts; the clock's four marks over Chapter 5's eight slices; the
# twelve worked answers scored by the rubric; the drill on the answer
# that spent the first half hour on the model, with the mock
# interviewer's questions replayed from fixtures; the failure
# injection (a level-four answer with no estimate scores below its
# level); the component-list rubric against the rubric; the two
# people's calibration; the model as a third scorer, replayed; the
# tiers; and the card. Offline by default. With RUN_LIVE=1 and
# ANTHROPIC_API_KEY set, the model scoring, the drill, and the live
# contract test call the pinned small model (about one cent).
set -euo pipefail
cd "$(dirname "$0")/.."
PY=${PYTHON:-python3}
if [ "${RUN_LIVE:-0}" = "1" ] && [ -n "${ANTHROPIC_API_KEY:-}" ]; then
    "$PY" -m ladder.live --record
    "$PY" -m ladder.drill --answer A03b --live > /dev/null
fi
for part in levels clock worked; do
    "$PY" -m ladder.demo --part "$part"
    echo
done
"$PY" -m ladder.demo --part drill --answer A03b
echo
"$PY" -m ladder.demo --part score --answer A08a
echo
# Failure injection: expected to score below the level.
"$PY" -m ladder.demo --part score --answer A08a --fault no-estimate \
    || true
echo
for part in v0 agree model tiers card; do
    "$PY" -m ladder.demo --part "$part"
    echo
done
echo "== tests =="
DESIGNLAB_OFFLINE=1 "$PY" -m unittest ladder.test_ladder \
    models.test_interviewer -v
if [ "${RUN_LIVE:-0}" = "1" ] && [ -n "${ANTHROPIC_API_KEY:-}" ]; then
    "$PY" -m unittest models.test_live_interviewer -v
fi
