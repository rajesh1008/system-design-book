#!/usr/bin/env bash
# Chapter 44 lab: the go-live replayed from the records. The pilot
# and its numbers; the ramp by task type against a ramp by share of
# traffic; the storm day of September 10, 2026 (41,000 changes in six
# hours) through the approval queue as run; the failure injection (a
# queue with no prioritization); the Try It Yourself runs (fare class
# instead of departure, no emergency budget, autonomy widened to
# $1,000); the incident record; the approval desk sized; recovery;
# and the fall card with the three designs that changed. Offline; no
# model call and no key.
set -euo pipefail
cd "$(dirname "$0")/.."
PY=${PYTHON:-python3}
for part in pilot ramp day; do
    "$PY" -m golive.demo --part "$part"
    echo
done
"$PY" -m golive.demo --part replay --scenario as-run
echo
# Failure injection: no prioritization all day. Departures are missed
# while the queue holds low-urgency refunds.
"$PY" -m golive.demo --part replay --scenario no-priority
echo
# Try It Yourself.
"$PY" -m golive.demo --part replay --order fare
echo
"$PY" -m golive.demo --part replay --no-emergency
echo
"$PY" -m golive.demo --part replay --widen 1000
echo
for part in compare levers record capacity recovery card; do
    "$PY" -m golive.demo --part "$part"
    echo
done
echo "== tests =="
DESIGNLAB_OFFLINE=1 "$PY" -m unittest golive.test_golive \
    capacity.test_approvals -v
