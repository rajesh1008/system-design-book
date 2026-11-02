"""Durable execution for one agent run (Chapter 9).

A run is a fixed sequence of steps. The run store keeps three things
outside the process: a checkpoint per step (position and the pending
approval, permission, and keys), a step journal (an intent row before
any effect, a result row after, and every model output), and durable
timers. Resume re-reads the permission before it acts; replay runs the
workflow from the journal and makes no model or tool calls.

Three strategies are built so they can be compared under the same
kills: "memory" (the pilot loop, state in the process), "framework"
(a checkpointer that saves messages and position, February 2026), and
"durable" (the platform-owned run store, revision 2 of R-001).
No live API calls anywhere in this package.
"""
