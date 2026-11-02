# designlab test results

Real output, pasted unedited from one run on November 2, 2026 (IST). Batch 0.
Command: `./run_all.sh` from `04-code/designlab`, with `ANTHROPIC_API_KEY` set in
the environment (its value appears nowhere in this file or the tree).

```text
run started 2026-11-02 11:58:15 UTC
Python 3.13.5
== offline unit tests
test_cli_exit_codes (bank.test_bank.TestIndex.test_cli_exit_codes) ... ok
test_reconcile (bank.test_bank.TestIndex.test_reconcile) ... ok
test_render_groups_and_points_to_chapters (bank.test_bank.TestIndex.test_render_groups_and_points_to_chapters) ... ok
test_render_refuses_a_question_with_no_chapter (bank.test_bank.TestIndex.test_render_refuses_a_question_with_no_chapter) ... ok
test_interview_voice_reference_parses (bank.test_bank.TestLoaders.test_interview_voice_reference_parses) ... ok
test_load_raises_on_bad_rows (bank.test_bank.TestLoaders.test_load_raises_on_bad_rows) ... ok
test_markup_fixture (bank.test_bank.TestLoaders.test_markup_fixture) ... ok
test_table_fixture (bank.test_bank.TestLoaders.test_table_fixture) ... ok
test_unclosed_block_fails (bank.test_bank.TestLoaders.test_unclosed_block_fails) ... ok
test_vocabularies (bank.test_bank.TestTaxonomy.test_vocabularies) ... ok
test_answer_shape_is_optional (bank.test_bank.TestValidate.test_answer_shape_is_optional) ... ok
test_duplicates_fail (bank.test_bank.TestValidate.test_duplicates_fail) ... ok
test_good_question_passes (bank.test_bank.TestValidate.test_good_question_passes) ... ok
test_id_shape_and_agreement (bank.test_bank.TestValidate.test_id_shape_and_agreement) ... ok
test_question_with_no_chapter_fails (bank.test_bank.TestValidate.test_question_with_no_chapter_fails) ... ok
test_unknown_values_fail (bank.test_bank.TestValidate.test_unknown_values_fail) ... ok
test_full_record_survives_timeout_with_one_credit (chain.test_chain.ChainTests.test_full_record_survives_timeout_with_one_credit) ... ok
test_pilot_loop_reproduces_the_double_refund (chain.test_chain.ChainTests.test_pilot_loop_reproduces_the_double_refund) ... ok
test_refuses_amount_above_permission (chain.test_chain.ChainTests.test_refuses_amount_above_permission) ... ok
test_refuses_permission_granted_by_the_actor (chain.test_chain.ChainTests.test_refuses_permission_granted_by_the_actor) ... ok
test_refuses_verification_by_the_actor (chain.test_chain.ChainTests.test_refuses_verification_by_the_actor) ... ok
test_refuses_without_permission_or_key (chain.test_chain.ChainTests.test_refuses_without_permission_or_key) ... ok
test_trail_is_hash_linked (chain.test_chain.ChainTests.test_trail_is_hash_linked) ... ok
test_unanswered_effect_is_not_counted_done (chain.test_chain.ChainTests.test_unanswered_effect_is_not_counted_done) ... ok
test_body_shape_and_completion (common.test_common.TestClient.test_body_shape_and_completion) ... ok
test_cache_hit_skips_transport_and_meter (common.test_common.TestClient.test_cache_hit_skips_transport_and_meter) ... ok
test_committed_fixture_replays (common.test_common.TestClient.test_committed_fixture_replays) ... ok
test_drift_is_visible (common.test_common.TestClient.test_drift_is_visible) ... ok
test_key_never_reaches_repr_errors_or_records (common.test_common.TestClient.test_key_never_reaches_repr_errors_or_records) ... ok
test_missing_key_raises_without_network (common.test_common.TestClient.test_missing_key_raises_without_network) ... ok
test_offline_switch_disables_live (common.test_common.TestClient.test_offline_switch_disables_live) ... ok
test_derived_seeds_differ_by_label (common.test_common.TestClockIdsRand.test_derived_seeds_differ_by_label) ... ok
test_fixed_clock_steps (common.test_common.TestClockIdsRand.test_fixed_clock_steps) ... ok
test_run_id_is_reproducible (common.test_common.TestClockIdsRand.test_run_id_is_reproducible) ... ok
test_prices_are_positive_and_ordered (common.test_common.TestModels.test_prices_are_positive_and_ordered) ... ok
test_roles_are_pinned (common.test_common.TestModels.test_roles_are_pinned) ... ok
test_unpinned_id_is_refused (common.test_common.TestModels.test_unpinned_id_is_refused) ... ok
test_committed_tree_is_clean (common.test_common.TestRedact.test_committed_tree_is_clean) ... ok
test_fixture_rules_are_stricter (common.test_common.TestRedact.test_fixture_rules_are_stricter) ... ok
test_masks_key_shapes_in_text (common.test_common.TestRedact.test_masks_key_shapes_in_text) ... ok
test_masks_secret_fields_but_not_token_counts (common.test_common.TestRedact.test_masks_secret_fields_but_not_token_counts) ... ok
test_masks_the_env_value_whatever_its_shape (common.test_common.TestRedact.test_masks_the_env_value_whatever_its_shape) ... ok
test_scan_tree_flags_a_planted_key (common.test_common.TestRedact.test_scan_tree_flags_a_planted_key) ... ok
test_cap_refuses_before_the_call (common.test_common.TestSpend.test_cap_refuses_before_the_call) ... ok
test_ledger_written (common.test_common.TestSpend.test_ledger_written) ... ok
test_price_arithmetic (common.test_common.TestSpend.test_price_arithmetic) ... ok
test_emit_refuses_long_lines (common.test_common.TestText.test_emit_refuses_long_lines) ... ok
test_chain_checks_and_redacts (common.test_common.TestTrail.test_chain_checks_and_redacts) ... ok
test_edit_delete_and_reorder_are_caught (common.test_common.TestTrail.test_edit_delete_and_reorder_are_caught) ... ok
test_file_backed (common.test_common.TestTrail.test_file_backed) ... ok
test_cache_repeat_makes_no_second_call (common.test_live.TestLiveClient.test_cache_repeat_makes_no_second_call) ... skipped 'ANTHROPIC_API_KEY not set (or DESIGNLAB_OFFLINE=1); live test skipped'
test_unknown_model_error_is_clean (common.test_live.TestLiveClient.test_unknown_model_error_is_clean) ... skipped 'ANTHROPIC_API_KEY not set (or DESIGNLAB_OFFLINE=1); live test skipped'
test_all_roles_covered (common.test_live.TestLivePins.test_all_roles_covered) ... skipped 'ANTHROPIC_API_KEY not set (or DESIGNLAB_OFFLINE=1); live test skipped'
test_dated (common.test_live.TestLivePins.test_dated) ... skipped 'ANTHROPIC_API_KEY not set (or DESIGNLAB_OFFLINE=1); live test skipped'
test_frontier (common.test_live.TestLivePins.test_frontier) ... skipped 'ANTHROPIC_API_KEY not set (or DESIGNLAB_OFFLINE=1); live test skipped'
test_mid (common.test_live.TestLivePins.test_mid) ... skipped 'ANTHROPIC_API_KEY not set (or DESIGNLAB_OFFLINE=1); live test skipped'
test_small (common.test_live.TestLivePins.test_small) ... skipped 'ANTHROPIC_API_KEY not set (or DESIGNLAB_OFFLINE=1); live test skipped'
test_anchor_flight_moved_eleven_hours_to_boston (corpus.test_corpus.TestAnchor.test_anchor_flight_moved_eleven_hours_to_boston) ... ok
test_anchor_has_no_permission_record_and_a_ticket (corpus.test_corpus.TestAnchor.test_anchor_has_no_permission_record_and_a_ticket) ... ok
test_the_refund_that_happened_twice (corpus.test_corpus.TestAnchor.test_the_refund_that_happened_twice) ... ok
test_memories_carry_provenance_and_expiry (corpus.test_corpus.TestContent.test_memories_carry_provenance_and_expiry) ... ok
test_planted_instructions_are_flagged (corpus.test_corpus.TestContent.test_planted_instructions_are_flagged) ... ok
test_policies (corpus.test_corpus.TestContent.test_policies) ... ok
test_timestamps_in_range_and_utc (corpus.test_corpus.TestContent.test_timestamps_in_range_and_utc) ... ok
test_other_seed_differs (corpus.test_corpus.TestDeterminism.test_other_seed_differs) ... ok
test_pinned_digest (corpus.test_corpus.TestDeterminism.test_pinned_digest) ... ok
test_same_seed_same_bytes (corpus.test_corpus.TestDeterminism.test_same_seed_same_bytes) ... ok
test_unknown_scale_refused (corpus.test_corpus.TestDeterminism.test_unknown_scale_refused) ... ok
test_write_matches_manifest (corpus.test_corpus.TestDeterminism.test_write_matches_manifest) ... ok
test_emails_are_reserved_domains (corpus.test_corpus.TestIntegrity.test_emails_are_reserved_domains) ... ok
test_foreign_keys_resolve (corpus.test_corpus.TestIntegrity.test_foreign_keys_resolve) ... ok
test_ids_have_house_shapes (corpus.test_corpus.TestIntegrity.test_ids_have_house_shapes) ... ok
test_primary_keys_unique (corpus.test_corpus.TestIntegrity.test_primary_keys_unique) ... ok
test_change_share_and_handlers (corpus.test_corpus.TestRatios.test_change_share_and_handlers) ... ok
test_handoff_flag_matches_handler (corpus.test_corpus.TestRatios.test_handoff_flag_matches_handler) ... ok
test_pilot_rules (corpus.test_corpus.TestRatios.test_pilot_rules) ... ok
test_refund_error_rate (corpus.test_corpus.TestRatios.test_refund_error_rate) ... ok
test_twelve_change_types_all_present (corpus.test_corpus.TestRatios.test_twelve_change_types_all_present) ... ok
test_demos_run_and_fit (test_demos.TestDemos.test_demos_run_and_fit) ... ok

----------------------------------------------------------------------
Ran 79 tests in 2.062s

OK (skipped=7)
== live tests
test_cache_repeat_makes_no_second_call (common.test_live.TestLiveClient.test_cache_repeat_makes_no_second_call) ... ok
test_unknown_model_error_is_clean (common.test_live.TestLiveClient.test_unknown_model_error_is_clean) ... ok
test_all_roles_covered (common.test_live.TestLivePins.test_all_roles_covered) ... ok
test_dated (common.test_live.TestLivePins.test_dated) ... ok
test_frontier (common.test_live.TestLivePins.test_frontier) ... ok
test_mid (common.test_live.TestLivePins.test_mid) ... ok
test_small (common.test_live.TestLivePins.test_small) ... ok

----------------------------------------------------------------------
Ran 7 tests in 5.375s

OK

live spend: billed calls=5 usd=0.000263
== secret scan
secret scan: 43 files, 0 with findings
exit code 0
```

## Demo output

Each demo run offline with `DESIGNLAB_OFFLINE=1`, straight after the suite.

### python3 -m common.demo

```text
run run-20260105T090000-bd4348  seed=2026

Pinned models (common/models.toml)
  small     claude-haiku-5-5            in $ 0.10  out $ 0.50 /Mtok
  mid       claude-sonnet-5-5           in $ 2.00  out $10.00 /Mtok
  frontier  claude-opus-5-5             in $ 4.00  out $20.00 /Mtok
  dated     claude-haiku-4-5-20251001   in $ 1.00  out $ 5.00 /Mtok

Trail: three entries, then one edited
  lines=3  check=[]
  line 2 api_key stored as [REDACTED]
  after edit: line 2: link broken (edited or removed line before it)

Spend meter: a replayed call, then a cap of $0.0001
  claude-haiku-5-5: 'ok'  tokens 17+4  $0.000004
  refused before sending:
  cap $0.0001, spent $0.0000, call up to $0.0124
```

### python3 -m corpus.demo

```text
Lakeshore corpus v0, seed 2026
digest 1eff42af7b9aaea13e893b18a2645e56
  carriers             140
  airports              50
  hotels             2,000
  policies               6
  customers          3,000
  flights            4,000
  itineraries        6,000
  contacts          10,000
  changes            1,500
  refunds              463
  settlement_lines     466
  tickets              300
  hotel_emails         300
  memories             600

Ratios (fixed by the style sheet)
  changes / contacts       15.0%
  handled by a person      61.0%
  handled by the pilot      2.0%
  refunds found wrong       0.9%  (4 of 463)

Change types
  voluntary-rebook           241
  involuntary-rebook         223
  cancel-with-refund         165
  involuntary-refund         149
  schedule-change-accept     142
  hotel-date-change          124
  cancel-for-credit          117
  hotel-cancel                94
  upgrade                     86
  car-rental-change           60
  ancillary-refund            55
  name-correction             44

The anchor: LTG-4471902
  2025-12-04T20:32:14Z  CR-00001  $412.60  REF-000043
  2025-12-04T20:32:17Z  CR-00002  $412.60  REF-000043
  (UTC; the first credit is 14:32:14 in Chicago)
  pilot refunds 11, with a permission record 9
  (chain records begin December 15, 2025)

Hotel emails carrying instruction-shaped text: 6
```

### python3 -m bank.demo

```text
bank: 10 questions; chapter markup: 3

By round
  phone-screen            Q1.1
  system-design           Q10.3
  distributed-systems     Q7.1
  agent-runtime           Q13.2
  control-plane-security  Q31.4
  evaluation-operations   Q4.2, Q34.1
  take-home               Q43.1
  bar-raiser              Q47.2
  hiring-manager          Q41.2

By type
  C concept      2
  S scenario     2
  T design       4
  K stakeholder  2

Chapter markup checked against the bank
  Q4.2: level 'staff' in chapter, 'L4' in bank
  Q41.2: level 'principal' in chapter, 'L6' in bank

A row with no chapter, an unknown round and a repeated ID
  FAIL Q9.1 (bad.md:3): no chapter
  FAIL Q9.1 (bad.md:3): unknown round 'lunch'
  FAIL Q9.1 (bad.md:4): duplicate of bad.md:3
```

### python3 -m chain.demo

```text
Thursday replay: LTG-4471902, refund $412.60
  pilot loop     credits=2  permission=none
  proposal only  credits=0  refused: permission, idempotency_key
  full record    credits=1  attempts=2  by=settlement-reconciler
  actor checks   credits=1  refused: independent verification

1,000 refunds, 2% answered after the 8.0 s timeout
  pilot loop  duplicates=23  permissions=0
  chain loop  duplicates=0  permissions=1,000  trail lines=1,000
```
