#!/usr/bin/env bash
# Chapter 36 lab: replay the June 24 hotel note through three configs,
# run the battery with the email case, show why the golden set missed
# it, activate the destination bundle, anchor a month of trail, build
# and attack the evidence pack, weigh the evidence, close the finding.
# Offline; the live part replays recorded fixtures and reads no key.
set -euo pipefail
cd "$(dirname "$0")/.."
PY=${PYTHON:-python3}
echo "== the hotel note, replayed: June 24, June 26, July plan =="
"$PY" -m assurance.demo --part replay
echo "== the battery with the email case =="
"$PY" -m assurance.demo --part battery
echo "== why the golden set could not fail =="
"$PY" -m assurance.demo --part golden
echo "== destination-v1: sign, shadow, activate, replay June =="
"$PY" -m assurance.demo --part bundle
echo "== a month of trail and its daily anchors =="
"$PY" -m assurance.demo --part anchor
echo "== the evidence pack for June =="
"$PY" -m assurance.demo --part pack
echo "== tampering with the trail and the pack =="
"$PY" -m assurance.demo --part tamper
echo "== the auditor's sample =="
"$PY" -m assurance.demo --part sample
echo "== which evidence is admissible =="
"$PY" -m assurance.demo --part evidence
echo "== the finding, opened to closed =="
"$PY" -m assurance.demo --part finding
echo "== the assurance card =="
"$PY" -m assurance.demo --part card
echo "== recorded live check: does a model follow the note? =="
"$PY" -m assurance.demo --part live
echo "== tests =="
DESIGNLAB_OFFLINE=1 "$PY" -m unittest assurance.test_assurance threats.test_threats -v
