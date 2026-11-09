# ch02 alt text (one line per figure; copied into 03-figures/alt.md for the build)
fig-02-1: Six states run down the left from output to business result, the five gaps are labeled on the arrows between them, and each state writes one linked line of the trail on the right.
fig-02-6: Sequence of the Thursday refund in which the processor credits the card, the framework times out and retries without a key, a second credit lands three seconds later, and the tool server reports status 200.
fig-02-2: Timeline comparing the dashboard's single 8.1-second call with the framework log's timed-out attempt and retry, with the two settlement credits marked beneath them.
fig-02-9: Class diagram of the six records, where each record points back to the one before it, the permission binds to the proposal, and the execution carries the permission's key.
fig-02-10: State diagram of a permission that is requested, then granted or denied, and once granted ends as spent by one execution, expired, or revoked.
fig-02-3: Gap one, where a typed proposal record separates model output from anything that can act, and acting on prose is the failure branch.
fig-02-4: Gap two, where a policy decision record separates a proposal from a permission, and self-approval is the failure branch.
fig-02-5: Gap three, where an idempotency key and a scope record separate a permission from execution, and a second effect is the failure branch.
fig-02-7: Gap four, where an independent read of the record of fact separates execution from a verified outcome, and the actor's self-report is the failure branch.
fig-02-8: Gap five, where a count of verified outcomes links a verified outcome to the business result, and a busy metric is the failure branch.
fig-02-11: Field-by-field comparison of one refund, where the pilot shows no permission, no key, two credits, and a status code, and the chain shows each field filled.
fig-02-12: Line chart where duplicate refunds per 1,000 rise with the share of calls answered after the timeout in the pilot loop and stay at zero in the chain loop.
