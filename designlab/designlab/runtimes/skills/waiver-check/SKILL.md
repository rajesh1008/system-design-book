---
name: waiver-check
description: Check whether a published waiver covers a disrupted trip before applying a change fee. Use on a schedule change or a weather event.
---
# Waiver check

1. Call `flight_status` for the segment. A delay alone is not a waiver.
2. Call `notice_read` for waivers active on the travel date. Match the
   waiver's dates, routes, and fare classes; all three must match.
3. If a waiver matches, cite its notice id in the note. The fee is
   whatever `fare_calc` returns with the waiver code applied.
4. If two waivers match, hand off; the desk picks.
