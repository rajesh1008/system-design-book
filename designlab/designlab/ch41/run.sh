#!/usr/bin/env bash
# Chapter 41 lab: the charter, the roster and the skills gap, the
# decision-rights matrix, six scenarios walked against three dated
# matrices, the failure injection (a policy change nobody can
# approve), the cost of the stall, the operating rhythm, the job
# market, and the team card. Offline; no model call and no key.
set -euo pipefail
cd "$(dirname "$0")/.."
PY=${PYTHON:-python3}
for part in charter roster gap; do
    "$PY" -m org.demo --part "$part"
    echo
done
"$PY" -m org.demo --part gap --hire june
echo
"$PY" -m org.demo --part gap --hire architect
echo
"$PY" -m org.demo --part matrix
echo
"$PY" -m org.demo --part scenarios --fault no-owner
echo
"$PY" -m org.demo --part scenarios --fault no-key
echo
"$PY" -m org.demo --part scenarios --matrix 2026-08-19
echo
"$PY" -m org.demo --part scenarios
echo
for part in stall rhythm market card; do
    "$PY" -m org.demo --part "$part"
    echo
done
echo "== tests =="
DESIGNLAB_OFFLINE=1 "$PY" -m unittest org.test_org bank.test_market -v
