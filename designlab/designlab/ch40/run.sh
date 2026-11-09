#!/usr/bin/env bash
# Chapter 40 lab: the agent platform. The project's control plane on
# August 10, the template, the extraction of servicing and the desk,
# loyalty on the golden path, the six conformance tests with and
# without the old ledger key, evidence-chain coverage, the two
# onboarding logs, platform economics, and the platform card.
# Offline: no model call and no key.
set -euo pipefail
cd "$(dirname "$0")/.."
PY=${PYTHON:-python3}
"$PY" -m agentplatform.demo --part project
echo
"$PY" -m agentplatform.demo --part template --as-built
echo
for part in template extract onboard conformance; do
    "$PY" -m agentplatform.demo --part "$part"
    echo
done
"$PY" -m agentplatform.demo --part conformance --bypass
echo
for part in chain onboarding economics; do
    "$PY" -m agentplatform.demo --part "$part"
    echo
done
"$PY" -m agentplatform.demo --part economics --charge
echo
"$PY" -m agentplatform.demo --part card
echo
echo "== tests =="
DESIGNLAB_OFFLINE=1 "$PY" -m unittest agentplatform.test_agentplatform -v
