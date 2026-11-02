#!/usr/bin/env bash
# Chapter 5 lab: the method as data. Offline tests, the demo, the Try
# It Yourself variations, then the secret scan. No live API calls.
set -euo pipefail
cd "$(dirname "$0")/.."
DESIGNLAB_OFFLINE=1 python3 -m unittest method.test_method
python3 -m method.demo
python3 -m method.demo --question "K5=Who may change the prompt?"
python3 -m method.demo --lint method/designs/demo-2025-10-06.toml || true
python3 -m common.secretscan
