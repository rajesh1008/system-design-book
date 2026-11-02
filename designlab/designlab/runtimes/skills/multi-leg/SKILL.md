---
name: multi-leg
description: Change one leg of a multi-leg trip without breaking the others. Use when a booking has more than one segment and the customer changes one.
---
# Multi-leg changes

1. Call `booking_read`; list every segment with its status.
2. Price the change with `fare_quote` for the changed leg and every
   leg priced through with it.
3. Rebook with `rebook_ticket` only after a permission covers the
   whole itinerary, not the one leg.
4. Verify each segment's new status with `booking_read` after the
   change; a segment left unticketed is a failure, not a success.
