"""spine: the asynchronous spine of Chapter 8.

In-process queues with ordering per key, backpressure from people,
tools and budgets, dead letters with an inbox, and the fan-out of one
airline cancellation. Standard library only; offline; no model call.

The spine moves messages. It never makes an effect exactly-once; the
tool and its idempotency key do that (Chapter 7). The inbox here only
stops one consumer from applying one message twice.
"""
