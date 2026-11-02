# Chapter 2 labs: the evidence chain

Run everything with `ch02/run.sh` from `04-code/designlab`.

| Command | What it shows |
|---|---|
| `python3 -m chain.demo` | The Thursday replay, then 1,000 refunds at `seed=7` (pilot loop against chain loop). Try `--n 10000 --seed 11`. |
| `python3 -m chain.incident` | Booking LTG-4471902 read from the dashboard, the framework log, and the processor settlement file in the corpus. |
| `python3 -m chain.lab --gaps` | One rebooking through six states, three forged chains, and the gap finder on five designs. |
| `python3 -m chain.live` | Real small-model output through the same parser and policy engine. Needs `ANTHROPIC_API_KEY` in the environment. |

Modules: `chain/record.py` (the six-field record), `chain/loop.py`
(pilot loop, chain loop, processor stand-in), `chain/states.py` (six
states, one record each), `chain/check.py` (gap finder and chain
checker), `chain/incident.py`, `chain/lab.py`, `chain/live.py`.

Failure injection: `run_rebooking(text, forge="self_verify")` has the
executor sign its own verified outcome; `forge="self_permit"` has the
parser write the permission. The checker must refuse both.
