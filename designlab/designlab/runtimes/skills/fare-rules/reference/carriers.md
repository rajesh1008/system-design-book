# Carriers with their own penalty tables (illustrative)

Lakeshore's fare desk keeps one page per carrier whose change and
refund penalties do not follow the fare basis. The skill reads the
page name from this file and the numbers from `fare_rules_search`.

| Carrier code | Page | Owner |
|---|---|---|
| LK1 | fare-desk/penalties/lk1 | Fare desk |
| LK2 | fare-desk/penalties/lk2 | Fare desk |
| LK3 | fare-desk/penalties/lk3 | Fare desk |

A carrier missing from this table follows its fare basis. A page
older than 90 days is stale; hand off and say so in the note.
