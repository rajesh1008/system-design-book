"""Tool-argument contracts (Chapter 16).

A tool call from the model passes three checks at the gateway's intake
before it becomes a proposal for the control plane (contract C2):

    schema   the shape: types, required fields, enums, patterns, no
             extra fields, money as a decimal string
    world    the references: every identifier exists, and the things it
             names belong together (ticket on itinerary, passenger on
             ticket, amount within the fare paid)
    repair   a rejected call goes back to the model with a structured
             reason, at most twice, and then to a person

Offline by default. `live.py` sends twenty argument cases to the small
pinned model with real tool definitions.
"""
