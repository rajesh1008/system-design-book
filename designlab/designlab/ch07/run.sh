#!/usr/bin/env bash
# Chapter 7 lab: offline tests, the demo, the failure injection (which
# must fail the checker), then the secret scan. No live API is used.
set -euo pipefail
cd "$(dirname "$0")/.."
DESIGNLAB_OFFLINE=1 python3 -m unittest corpus.test_tools effects.test_effects
python3 -m effects.demo
python3 -m effects.demo sweep
if python3 -m effects.demo replay --inject no-key; then
  echo "injection did not fail the checker" >&2
  exit 1
fi
echo "injection failed the checker, as it should"
python3 -m common.secretscan
