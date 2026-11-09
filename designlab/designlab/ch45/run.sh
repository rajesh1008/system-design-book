#!/usr/bin/env bash
# Chapter 45 lab: six internal designs (research, coding, analytics,
# IT operations, compliance, reconciliation) added to Chapter 43's six
# with designs.register and designs.register_rule, without editing
# Chapter 43's files; the loop, privilege, and record rules; the
# failure injection (an unattended loop with no persisted state); the
# Try It Yourself runs (change control removed, a research run with
# no budget, raw SQL in place of the semantic layer); the patterns
# across twelve designs; the internal costs; the reconciliation
# numbers; the review records; and the card. Offline; no model call
# and no key.
set -euo pipefail
cd "$(dirname "$0")/.."
PY=${PYTHON:-python3}
for part in method design lint loops privilege; do
    "$PY" -m designs.demo45 --part "$part"
    echo
done
# Failure injection: each of these is expected to fail the linter.
for fault in no-state no-change-control no-budget raw-sql; do
    "$PY" -m designs.demo45 --part lint --fault "$fault" || true
    echo
done
for part in patterns cost recon records card; do
    "$PY" -m designs.demo45 --part "$part"
    echo
done
echo "== tests =="
DESIGNLAB_OFFLINE=1 "$PY" -m unittest designs.test_internal -v
