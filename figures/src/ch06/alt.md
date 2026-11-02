# ch06 alt text (one line per figure; copied into 03-figures/alt.md for the build)
fig-06-1: The four planes on one page, where the knowledge plane feeds the agent loop, the loop proposes to the control plane, only a permission opens the gateway to the systems of record, and the trail's verifier reads those systems directly.
fig-06-2: The agent process holds only the model and the loop, while the policy engine, the approver desk, and identity and budgets sit in a separate control process whose permission the gateway redeems before acting.
fig-06-3: Class diagram of what crosses each plane boundary, from the context packet through the proposal, decision, permission, and effect record to the trail line and the verification, with each arrow labeled by its contract.
fig-06-4: Sequence of a refund where the customer waits while the approver answers; an answer within 120 seconds leads to a permission and an effect, and no answer queues the case with a 60 minute promise.
fig-06-5: Sequence of a rebooking the agent completes inside its limit and announces, after which a refusal within 24 hours goes to the agent desk queue for a person to work later.
fig-06-6: Sequence of the planned unattended fare-watch path, where a schedule starts the loop, the policy engine checks the cap and daily budget before granting, and a five percent sample reaches auditors the next day.
fig-06-7: Four kinds of people and where they enter, with the agent desk taking over in the action plane, approvers and policy owners in the control plane, and auditors sampling the trail later.
fig-06-8: A table of the six edges of the reference diagram, each with its contract, the planes it joins, and the unit test that enforces it, so that no contract is left untested.
fig-06-9: A grid of the five evidence chain gaps against the four planes, showing which plane owns, feeds, or writes down each gap, with no plane owning the final business result.
fig-06-10: The agent loop has a recorded path through the gateway to the payment processor and a hidden fast refund tool that reaches the processor directly, issuing 26 refunds worth $3,295.48 with no permission.
fig-06-11: A table of four task types showing the autonomy level each runs at on a four step ladder, whether its hand-off is synchronous or asynchronous, and the first state the customer sees.
