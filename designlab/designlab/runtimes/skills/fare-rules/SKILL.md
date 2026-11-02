---
name: fare-rules
description: Read a fare's change and refund rules before quoting an amount. Use when a customer asks what a change or refund costs.
---
# Fare rules

1. Call `booking_read` for the fare basis and the ticketing date.
2. Call `fare_rules_search` with the fare basis. Quote the rule text
   with its rule id; never paraphrase a penalty.
3. Amounts come from `fare_calc` and nowhere else. If the rule and the
   calculation disagree, hand off with both in the note.
4. For a carrier with its own penalty table, read
   reference/carriers.md for the table's location, not its numbers.

Do not decide eligibility from memory of earlier cases. A rule read
in this case is the only rule that counts.
