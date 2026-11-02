#!/usr/bin/env bash
# Chapter 1 lab: offline tests, the demo, live test if a key is set,
# then the secret scan. Run from anywhere.
set -euo pipefail
cd "$(dirname "$0")/.."
DESIGNLAB_OFFLINE=1 python3 -m unittest ch01.test_ch01
python3 -m ch01.demo
if [ -n "${ANTHROPIC_API_KEY:-}" ]; then
  python3 -m unittest ch01.test_live_ch01 -v
  python3 -m ch01.demo --live | sed -n '/^5\./,$p'
fi
python3 -m common.secretscan
