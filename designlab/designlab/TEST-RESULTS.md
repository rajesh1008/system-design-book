# designlab test results

Real output, pasted unedited from one run on November 2, 2026 (IST), Part I integration.
Run from a clean checkout of commit a72f2de ("Part I integration"), so untracked work in
progress in the working tree is not included. Command: `./run_all.sh` from
`04-code/designlab`, with `ANTHROPIC_API_KEY` set in the environment (its value
appears nowhere in this file or the tree). Summary: 282 offline tests OK (9 live
tests skipped offline), 9 live tests OK, live spend about $0.0003, six Part I demos
ok, secret scan 135 files with 0 findings.

```text
run started 2026-11-02 13:34:43 UTC
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
test_abandons_fail_too (baseline.test_baseline.TestAutonomy.test_abandons_fail_too) ... ok
test_baseline_autonomy_is_zero (baseline.test_baseline.TestAutonomy.test_baseline_autonomy_is_zero) ... ok
test_honest_definition_passes (baseline.test_baseline.TestAutonomy.test_honest_definition_passes) ... ok
test_vendor_and_honest (baseline.test_baseline.TestAutonomy.test_vendor_and_honest) ... ok
test_vendor_definition_fails (baseline.test_baseline.TestAutonomy.test_vendor_definition_fails) ... ok
test_blend_is_recomposed (baseline.test_baseline.TestCost.test_blend_is_recomposed) ... ok
test_labor_cross_check_within_two_percent (baseline.test_baseline.TestCost.test_labor_cross_check_within_two_percent) ... ok
test_paths (baseline.test_baseline.TestCost.test_paths) ... ok
test_rework_is_not_optional (baseline.test_baseline.TestCost.test_rework_is_not_optional) ... ok
test_ten_percent_person_cost (baseline.test_baseline.TestCost.test_ten_percent_person_cost) ... ok
test_dot_clock (baseline.test_baseline.TestErrors.test_dot_clock) ... ok
test_email_only_carriers_worse (baseline.test_baseline.TestErrors.test_email_only_carriers_worse) ... ok
test_later_as_of_finds_more (baseline.test_baseline.TestErrors.test_later_as_of_finds_more) ... ok
test_matured_rate_is_point_eight (baseline.test_baseline.TestErrors.test_matured_rate_is_point_eight) ... ok
test_naive_rate_undercounts (baseline.test_baseline.TestErrors.test_naive_rate_undercounts) ... ok
test_every_number_has_an_owner (baseline.test_baseline.TestScoreboard.test_every_number_has_an_owner) ... ok
test_row (baseline.test_baseline.TestScoreboard.test_row) ... ok
test_contacts_are_not_changes (baseline.test_baseline.TestVolume.test_contacts_are_not_changes) ... ok
test_logs_must_agree (baseline.test_baseline.TestVolume.test_logs_must_agree) ... ok
test_mix_matches_chapter_one (baseline.test_baseline.TestVolume.test_mix_matches_chapter_one) ... ok
test_person_share (baseline.test_baseline.TestVolume.test_person_share) ... ok
test_demo_shape_answers_none_of_the_questions (ch01.test_ch01.CheckerTests.test_demo_shape_answers_none_of_the_questions) ... ok
test_edited_trail_line_is_found (ch01.test_ch01.CheckerTests.test_edited_trail_line_is_found) ... ok
test_removing_the_check_loses_permission_but_not_verify (ch01.test_ch01.CheckerTests.test_removing_the_check_loses_permission_but_not_verify) ... ok
test_v0_has_no_action_without_a_permission_record (ch01.test_ch01.CheckerTests.test_v0_has_no_action_without_a_permission_record) ... ok
test_lab_clocks_carry_the_chicago_offset_for_the_day (ch01.test_ch01.ClockTests.test_lab_clocks_carry_the_chicago_offset_for_the_day) ... ok
test_trail_lines_carry_the_offset (ch01.test_ch01.ClockTests.test_trail_lines_carry_the_offset) ... ok
test_lab_output_fits_the_page (ch01.test_ch01.DemoTests.test_lab_output_fits_the_page) ... ok
test_live_path_with_a_scripted_transport (ch01.test_ch01.DemoTests.test_live_path_with_a_scripted_transport) ... ok
test_an_answer_reaches_nothing (ch01.test_ch01.LoopTests.test_an_answer_reaches_nothing) ... ok
test_demo_shape_duplicates_on_a_late_answer (ch01.test_ch01.LoopTests.test_demo_shape_duplicates_on_a_late_answer) ... ok
test_execute_without_permission_is_refused_and_trailed (ch01.test_ch01.LoopTests.test_execute_without_permission_is_refused_and_trailed) ... ok
test_one_refund_writes_six_lines_and_one_effect (ch01.test_ch01.LoopTests.test_one_refund_writes_six_lines_and_one_effect) ... ok
test_over_the_limit_goes_to_a_person (ch01.test_ch01.LoopTests.test_over_the_limit_goes_to_a_person) ... ok
test_permission_granted_by_the_actor_is_refused (ch01.test_ch01.LoopTests.test_permission_granted_by_the_actor_is_refused) ... ok
test_plain_text_is_an_answer (ch01.test_ch01.OutputTests.test_plain_text_is_an_answer) ... ok
test_prose_around_json_still_parses (ch01.test_ch01.OutputTests.test_prose_around_json_still_parses) ... ok
test_tool_json_is_an_action (ch01.test_ch01.OutputTests.test_tool_json_is_an_action) ... ok
test_truncated_json_fails_closed (ch01.test_ch01.OutputTests.test_truncated_json_fails_closed) ... ok
test_unknown_action_is_an_answer (ch01.test_ch01.OutputTests.test_unknown_action_is_an_answer) ... ok
test_model_proposes_and_v0_does_the_rest (ch01.test_live_ch01.TestLiveV0.test_model_proposes_and_v0_does_the_rest) ... skipped 'ANTHROPIC_API_KEY not set (or DESIGNLAB_OFFLINE=1); live test skipped'
test_full_record_survives_timeout_with_one_credit (chain.test_chain.ChainTests.test_full_record_survives_timeout_with_one_credit) ... ok
test_pilot_loop_reproduces_the_double_refund (chain.test_chain.ChainTests.test_pilot_loop_reproduces_the_double_refund) ... ok
test_refuses_amount_above_permission (chain.test_chain.ChainTests.test_refuses_amount_above_permission) ... ok
test_refuses_permission_granted_by_the_actor (chain.test_chain.ChainTests.test_refuses_permission_granted_by_the_actor) ... ok
test_refuses_verification_by_the_actor (chain.test_chain.ChainTests.test_refuses_verification_by_the_actor) ... ok
test_refuses_without_permission_or_key (chain.test_chain.ChainTests.test_refuses_without_permission_or_key) ... ok
test_trail_is_hash_linked (chain.test_chain.ChainTests.test_trail_is_hash_linked) ... ok
test_unanswered_effect_is_not_counted_done (chain.test_chain.ChainTests.test_unanswered_effect_is_not_counted_done) ... ok
test_clean_chain (chain.test_check.TestChainCheck.test_clean_chain) ... ok
test_edit_after_the_fact_breaks_link (chain.test_check.TestChainCheck.test_edit_after_the_fact_breaks_link) ... ok
test_missing_state (chain.test_check.TestChainCheck.test_missing_state) ... ok
test_self_granted_permission_fails (chain.test_check.TestChainCheck.test_self_granted_permission_fails) ... ok
test_self_signed_verification_fails (chain.test_check.TestChainCheck.test_self_signed_verification_fails) ... ok
test_chain_design_has_none (chain.test_check.TestGapFinder.test_chain_design_has_none) ... ok
test_missing_record_opens_gap (chain.test_check.TestGapFinder.test_missing_record_opens_gap) ... ok
test_pilot_has_two_open (chain.test_check.TestGapFinder.test_pilot_has_two_open) ... ok
test_second_settings (chain.test_check.TestGapFinder.test_second_settings) ... ok
test_every_agent_refund_after_chain_live_has_permission (chain.test_check.TestIncident.test_every_agent_refund_after_chain_live_has_permission) ... ok
test_report_fits (chain.test_check.TestIncident.test_report_fits) ... ok
test_two_credits_three_seconds_apart (chain.test_check.TestIncident.test_two_credits_three_seconds_apart) ... ok
test_model_words_never_grant (chain.test_live_chain.TestLiveChain.test_model_words_never_grant) ... skipped 'ANTHROPIC_API_KEY not set (or DESIGNLAB_OFFLINE=1); live test skipped'
test_empty_output_is_not_a_proposal (chain.test_states.TestStates.test_empty_output_is_not_a_proposal) ... ok
test_full_run_links_every_record (chain.test_states.TestStates.test_full_run_links_every_record) ... ok
test_lab_flights_leave_after_the_rebooking_moment (chain.test_states.TestStates.test_lab_flights_leave_after_the_rebooking_moment) ... ok
test_lab_lines_fit (chain.test_states.TestStates.test_lab_lines_fit) ... ok
test_parser_drops_claimed_approval (chain.test_states.TestStates.test_parser_drops_claimed_approval) ... ok
test_permission_bound_to_proposal_hash (chain.test_states.TestStates.test_permission_bound_to_proposal_hash) ... ok
test_policy_refuses_other_route (chain.test_states.TestStates.test_policy_refuses_other_route) ... ok
test_six_states_five_gaps (chain.test_states.TestStates.test_six_states_five_gaps) ... ok
test_slow_first_call_ticketed_once (chain.test_states.TestStates.test_slow_first_call_ticketed_once) ... ok
test_verifier_cannot_write (chain.test_states.TestStates.test_verifier_cannot_write) ... ok
test_without_keys_the_verifier_sees_two_tickets (chain.test_states.TestStates.test_without_keys_the_verifier_sees_two_tickets) ... ok
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
test_handle_cost_matches_chapter_4 (corpus.test_corpus.TestDeterminism.test_handle_cost_matches_chapter_4) ... ok
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
test_deterministic (corpus.test_ops.TestOpsCorpus.test_deterministic) ... ok
test_every_table_present (corpus.test_ops.TestOpsCorpus.test_every_table_present) ... ok
test_other_seed_differs (corpus.test_ops.TestOpsCorpus.test_other_seed_differs) ... ok
test_pinned (corpus.test_ops.TestOpsCorpus.test_pinned) ... ok
test_v0_untouched (corpus.test_ops.TestOpsCorpus.test_v0_untouched) ... ok
test_eighteen_tools_three_contracts (corpus.test_tools.ToolsTest.test_eighteen_tools_three_contracts) ... ok
test_lookup_respects_visibility (corpus.test_tools.ToolsTest.test_lookup_respects_visibility) ... ok
test_lost_request_leaves_no_record (corpus.test_tools.ToolsTest.test_lost_request_leaves_no_record) ... ok
test_native_key_conflict (corpus.test_tools.ToolsTest.test_native_key_conflict) ... ok
test_native_key_replays_receipt (corpus.test_tools.ToolsTest.test_native_key_replays_receipt) ... ok
test_none_contract_ignores_key (corpus.test_tools.ToolsTest.test_none_contract_ignores_key) ... ok
test_committed_key_is_not_called_again (effects.test_effects.ExecutorTest.test_committed_key_is_not_called_again) ... ok
test_expired_key_is_not_replayed (effects.test_effects.ExecutorTest.test_expired_key_is_not_replayed) ... ok
test_lookup_absent_then_attempts_again (effects.test_effects.ExecutorTest.test_lookup_absent_then_attempts_again) ... ok
test_lookup_finds_late_effect (effects.test_effects.ExecutorTest.test_lookup_finds_late_effect) ... ok
test_message_is_at_most_once (effects.test_effects.ExecutorTest.test_message_is_at_most_once) ... ok
test_native_timeout_replays_key (effects.test_effects.ExecutorTest.test_native_timeout_replays_key) ... ok
test_none_contract_escalates_not_retries (effects.test_effects.ExecutorTest.test_none_contract_escalates_not_retries) ... ok
test_new_permission_new_key (effects.test_effects.KeyTest.test_new_permission_new_key) ... ok
test_no_permission_no_key (effects.test_effects.KeyTest.test_no_permission_no_key) ... ok
test_permission_cannot_cover_other_request (effects.test_effects.KeyTest.test_permission_cannot_cover_other_request) ... ok
test_same_permission_same_key (effects.test_effects.KeyTest.test_same_permission_same_key) ... ok
test_conflict_on_fingerprint (effects.test_effects.LedgerTest.test_conflict_on_fingerprint) ... ok
test_illegal_move (effects.test_effects.LedgerTest.test_illegal_move) ... ok
test_stale_lease_refused (effects.test_effects.LedgerTest.test_stale_lease_refused) ... ok
test_keyed_replay_has_no_duplicates (effects.test_effects.ReplayTest.test_keyed_replay_has_no_duplicates) ... ok
test_no_key_injection_fails_the_checker (effects.test_effects.ReplayTest.test_no_key_injection_fails_the_checker) ... ok
test_unkeyed_replay_duplicates (effects.test_effects.ReplayTest.test_unkeyed_replay_duplicates) ... ok
test_break_compensates_in_reverse (effects.test_effects.SagaTest.test_break_compensates_in_reverse) ... ok
test_pilot_order_strands (effects.test_effects.SagaTest.test_pilot_order_strands) ... ok
test_safe_order_strands_nobody (effects.test_effects.SagaTest.test_safe_order_strands_nobody) ... ok
test_isolated_session_reaches_one_itinerary (isolation.test_isolation.TestBlast.test_isolated_session_reaches_one_itinerary) ... ok
test_littles_law_pool (isolation.test_isolation.TestBlast.test_littles_law_pool) ... ok
test_scoped_view_refuses_other_itineraries (isolation.test_isolation.TestBlast.test_scoped_view_refuses_other_itineraries) ... ok
test_shared_cache_reaches_every_cached_entry (isolation.test_isolation.TestBlast.test_shared_cache_reaches_every_cached_entry) ... ok
test_shared_dir_reaches_the_worker_shift (isolation.test_isolation.TestBlast.test_shared_dir_reaches_the_worker_shift) ... ok
test_unscoped_knowledge_reaches_everything (isolation.test_isolation.TestBlast.test_unscoped_knowledge_reaches_everything) ... ok
test_demo_lines_fit (isolation.test_isolation.TestDemo.test_demo_lines_fit) ... ok
test_deny_by_default (isolation.test_isolation.TestEgress.test_deny_by_default) ... ok
test_eleven_hosts_with_an_owner (isolation.test_isolation.TestEgress.test_eleven_hosts_with_an_owner) ... ok
test_every_denial_is_on_the_trail (isolation.test_isolation.TestEgress.test_every_denial_is_on_the_trail) ... ok
test_host_is_normalized (isolation.test_isolation.TestEgress.test_host_is_normalized) ... ok
test_listed_tool_and_host_allowed (isolation.test_isolation.TestEgress.test_listed_tool_and_host_allowed) ... ok
test_redirect_checked_hop_by_hop (isolation.test_isolation.TestEgress.test_redirect_checked_hop_by_hop) ... ok
test_tool_must_be_listed_for_the_host (isolation.test_isolation.TestEgress.test_tool_must_be_listed_for_the_host) ... ok
test_environment_is_empty (isolation.test_isolation.TestSandbox.test_environment_is_empty) ... ok
test_tool_cannot_open_a_socket (isolation.test_isolation.TestSandbox.test_tool_cannot_open_a_socket) ... ok
test_tool_cannot_write_into_another_session (isolation.test_isolation.TestSandbox.test_tool_cannot_write_into_another_session) ... ok
test_tool_writes_inside_its_own_dir (isolation.test_isolation.TestSandbox.test_tool_writes_inside_its_own_dir) ... ok
test_close_removes_the_dir (isolation.test_isolation.TestSessions.test_close_removes_the_dir) ... ok
test_injected_shared_dir_fails_the_suite (isolation.test_isolation.TestSessions.test_injected_shared_dir_fails_the_suite) ... ok
test_one_private_dir_per_session (isolation.test_isolation.TestSessions.test_one_private_dir_per_session) ... ok
test_session_id_is_never_reused (isolation.test_isolation.TestSessions.test_session_id_is_never_reused) ... ok
test_suite_finds_no_cross_reads (isolation.test_isolation.TestSessions.test_suite_finds_no_cross_reads) ... ok
test_demo_lines_and_exit (map.test_map.TestDemo.test_demo_lines_and_exit) ... ok
test_counts (map.test_map.TestMap.test_counts) ... ok
test_every_claim_dated_and_sourced (map.test_map.TestMap.test_every_claim_dated_and_sourced) ... ok
test_nothing_closes_g4_or_g5 (map.test_map.TestMap.test_nothing_closes_g4_or_g5) ... ok
test_struck_row (map.test_map.TestMap.test_struck_row) ... ok
test_aging_six_months_flags_shortlist (map.test_map.TestShortlist.test_aging_six_months_flags_shortlist) ... ok
test_exclusions_have_reasons (map.test_map.TestShortlist.test_exclusions_have_reasons) ... ok
test_lockin_twice_keeps_shortlist (map.test_map.TestShortlist.test_lockin_twice_keeps_shortlist) ... ok
test_score (map.test_map.TestShortlist.test_score) ... ok
test_shortlist (map.test_map.TestShortlist.test_shortlist) ... ok
test_bad_rows_refused (map.test_map.TestValidator.test_bad_rows_refused) ... ok
test_duplicate_id_refused (map.test_map.TestValidator.test_duplicate_id_refused) ... ok
test_future_claim_refused (map.test_map.TestValidator.test_future_claim_refused) ... ok
test_undated_claim_refused (map.test_map.TestValidator.test_undated_claim_refused) ... ok
test_unknown_gap_code_and_source (map.test_map.TestValidator.test_unknown_gap_code_and_source) ... ok
test_well_formed_row_loads (map.test_map.TestValidator.test_well_formed_row_loads) ... ok
test_dates_stay_strings_and_comments_drop (map.test_map.TestYamlish.test_dates_stay_strings_and_comments_drop) ... ok
test_duplicate_key_and_tab_refused (map.test_map.TestYamlish.test_duplicate_key_and_tab_refused) ... ok
test_nested_lists_and_flow_maps (map.test_map.TestYamlish.test_nested_lists_and_flow_maps) ... ok
test_clock_is_forty_five_minutes_without_gaps (method.test_method.Artifacts.test_clock_is_forty_five_minutes_without_gaps) ... ok
test_eight_artifacts_and_twelve_checks (method.test_method.Artifacts.test_eight_artifacts_and_twelve_checks) ... ok
test_first_ten_are_in_the_bank (method.test_method.Artifacts.test_first_ten_are_in_the_bank) ... ok
test_added_question (method.test_method.Demo.test_added_question) ... ok
test_demo_lines_fit_and_summary (method.test_method.Demo.test_demo_lines_fit_and_summary) ... ok
test_demo_design_fails_most_checks (method.test_method.Designs.test_demo_design_fails_most_checks) ... ok
test_estimate_values (method.test_method.Designs.test_estimate_values) ... ok
test_model_calls_do_not_move_reviewers (method.test_method.Designs.test_model_calls_do_not_move_reviewers) ... ok
test_sensitivity_names_storm_days_first (method.test_method.Designs.test_sensitivity_names_storm_days_first) ... ok
test_v0_1_passes (method.test_method.Designs.test_v0_1_passes) ... ok
test_v0_fails_exactly_three (method.test_method.Designs.test_v0_fails_exactly_three) ... ok
test_arithmetic (method.test_method.Formulas.test_arithmetic) ... ok
test_unknown_name_and_calls_are_refused (method.test_method.Formulas.test_unknown_name_and_calls_are_refused) ... ok
test_ungated_effect (method.test_method.Grammar.test_ungated_effect) ... ok
test_unknown_kind (method.test_method.Grammar.test_unknown_kind) ... ok
test_verifier_reading_the_actors_output (method.test_method.Grammar.test_verifier_reading_the_actors_output) ... ok
test_bad_formula (method.test_method.Rules.test_bad_formula) ... ok
test_dangling_link (method.test_method.Rules.test_dangling_link) ... ok
test_missing_assumption (method.test_method.Rules.test_missing_assumption) ... ok
test_missing_gap_answer (method.test_method.Rules.test_missing_gap_answer) ... ok
test_new_bank_question_fails_every_design (method.test_method.Rules.test_new_bank_question_fails_every_design) ... ok
test_open_question_with_owner_passes (method.test_method.Rules.test_open_question_with_owner_passes) ... ok
test_owner_not_listed (method.test_method.Rules.test_owner_not_listed) ... ok
test_record_needs_reversal (method.test_method.Rules.test_record_needs_reversal) ... ok
test_rejected_option_needs_a_reason (method.test_method.Rules.test_rejected_option_needs_a_reason) ... ok
test_thin_deep_dive (method.test_method.Rules.test_thin_deep_dive) ... ok
test_ceiling_rule (planes.test_planes.Autonomy.test_ceiling_rule) ... ok
test_customer_states_come_from_the_chain (planes.test_planes.Autonomy.test_customer_states_come_from_the_chain) ... ok
test_daily_budget_escalates_vouchers (planes.test_planes.Autonomy.test_daily_budget_escalates_vouchers) ... ok
test_no_task_type_runs_above_its_ceiling (planes.test_planes.Autonomy.test_no_task_type_runs_above_its_ceiling) ... ok
test_raising_refunds_fails (planes.test_planes.Autonomy.test_raising_refunds_fails) ... ok
test_signed_override_with_expiry_is_accepted (planes.test_planes.Autonomy.test_signed_override_with_expiry_is_accepted) ... ok
test_table_is_within_every_ceiling (planes.test_planes.Autonomy.test_table_is_within_every_ceiling) ... ok
test_unattended_needs_limit_budget_and_audit (planes.test_planes.Autonomy.test_unattended_needs_limit_budget_and_audit) ... ok
test_unattended_tasks_are_counted_as_agent_only_when_verified (planes.test_planes.Autonomy.test_unattended_tasks_are_counted_as_agent_only_when_verified) ... ok
test_c1_context_flags_stale_and_refuses_unknown (planes.test_planes.Contracts.test_c1_context_flags_stale_and_refuses_unknown) ... ok
test_c2_every_proposal_gets_one_decision (planes.test_planes.Contracts.test_c2_every_proposal_gets_one_decision) ... ok
test_c3_gateway_refuses_foreign_or_altered_permission (planes.test_planes.Contracts.test_c3_gateway_refuses_foreign_or_altered_permission) ... ok
test_c4_every_effect_has_a_trail_line (planes.test_planes.Contracts.test_c4_every_effect_has_a_trail_line) ... ok
test_c5_every_decision_is_written (planes.test_planes.Contracts.test_c5_every_decision_is_written) ... ok
test_c6_done_only_when_verified_by_non_actor (planes.test_planes.Contracts.test_c6_done_only_when_verified_by_non_actor) ... ok
test_customer_state_never_done_on_actor_says_so (planes.test_planes.Contracts.test_customer_state_never_done_on_actor_says_so) ... ok
test_every_contract_names_an_existing_test (planes.test_planes.Contracts.test_every_contract_names_an_existing_test) ... ok
test_bypass_effects_carry_no_permission (planes.test_planes.PathTest.test_bypass_effects_carry_no_permission) ... ok
test_clean_wiring_has_no_unmediated_path (planes.test_planes.PathTest.test_clean_wiring_has_no_unmediated_path) ... ok
test_injected_fast_path_is_found_both_ways (planes.test_planes.PathTest.test_injected_fast_path_is_found_both_ways) ... ok
test_policy_inside_the_loop_is_refused (planes.test_planes.PathTest.test_policy_inside_the_loop_is_refused) ... ok
test_undeclared_tool_shows_as_unknown_system (planes.test_planes.PathTest.test_undeclared_tool_shows_as_unknown_system) ... ok
test_admit_only_lowers (spine.test_spine.Backpressure.test_admit_only_lowers) ... ok
test_alert_and_reserve_keep_the_promise (spine.test_spine.Backpressure.test_alert_and_reserve_keep_the_promise) ... ok
test_cap_holds_and_never_drops (spine.test_spine.Backpressure.test_cap_holds_and_never_drops) ... ok
test_cap_is_derived (spine.test_spine.Backpressure.test_cap_is_derived) ... ok
test_no_cap_serves_stale_cards (spine.test_spine.Backpressure.test_no_cap_serves_stale_cards) ... ok
test_poison_parks_only_its_itinerary (spine.test_spine.DeadLetters.test_poison_parks_only_its_itinerary) ... ok
test_replay_in_order_and_idempotent (spine.test_spine.DeadLetters.test_replay_in_order_and_idempotent) ... ok
test_transient_retries_then_quarantines (spine.test_spine.DeadLetters.test_transient_retries_then_quarantines) ... ok
test_demo_runs_offline_and_fits_70 (spine.test_spine.Demo.test_demo_runs_offline_and_fits_70) ... ok
test_redelivered_event_adds_nothing (spine.test_spine.FanOut.test_redelivered_event_adds_nothing) ... ok
test_three_queues_and_counts (spine.test_spine.FanOut.test_three_queues_and_counts) ... ok
test_duplicate_and_stale (spine.test_spine.Inboxes.test_duplicate_and_stale) ... ok
test_coalesce_keeps_newest (spine.test_spine.Ordering.test_coalesce_keeps_newest) ... ok
test_same_key_same_partition (spine.test_spine.Ordering.test_same_key_same_partition) ... ok
test_stale_event_is_rejected (spine.test_spine.Ordering.test_stale_event_is_rejected) ... ok
test_zero_out_of_order_in_100k_shuffled (spine.test_spine.Ordering.test_zero_out_of_order_in_100k_shuffled) ... ok
test_demos_run_and_fit (test_demos.TestDemos.test_demos_run_and_fit) ... ok

----------------------------------------------------------------------
Ran 282 tests in 14.155s

OK (skipped=9)
== live tests
test_model_proposes_and_v0_does_the_rest (ch01.test_live_ch01.TestLiveV0.test_model_proposes_and_v0_does_the_rest) ... ok
test_model_words_never_grant (chain.test_live_chain.TestLiveChain.test_model_words_never_grant) ... ok
test_cache_repeat_makes_no_second_call (common.test_live.TestLiveClient.test_cache_repeat_makes_no_second_call) ... ok
test_unknown_model_error_is_clean (common.test_live.TestLiveClient.test_unknown_model_error_is_clean) ... ok
test_all_roles_covered (common.test_live.TestLivePins.test_all_roles_covered) ... ok
test_dated (common.test_live.TestLivePins.test_dated) ... ok
test_frontier (common.test_live.TestLivePins.test_frontier) ... ok
test_mid (common.test_live.TestLivePins.test_mid) ... ok
test_small (common.test_live.TestLivePins.test_small) ... ok

----------------------------------------------------------------------
Ran 9 tests in 12.320s

OK

live reply: {"action": "refund", "itinerary": "LTG-4471902", "amount_usd
live spend: billed calls=1 usd=0.000039

live spend: billed calls=5 usd=0.000263
== Part I demos (offline)
ok  ch01.demo
ok  chain.demo
ok  map.demo
ok  baseline.demo
ok  method.demo
ok  planes.demo
== secret scan
secret scan: 135 files, 0 with findings
```

## Demo output

Each demo run on its own from the same clean checkout; exit codes shown.

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
exit 0
```

### python3 -m corpus.demo

```text
Lakeshore corpus v0, seed 2026
digest f26e2b00cf62306affb44882a740e004
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
exit 0
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
exit 0
```

### python3 -m ch01.demo

```text
1. The October 6 demo, replayed (one rebooking)
   1 tool_call    tool=rebook status=200
  trail cannot answer: allowed, policy, once, verified

2. v0, one refund end to end (first answer arrives late)
   1 output       class=action
   2 proposal     refund LTG-4471902 $412.60
   3 permission   PRM-20931 by policy-engine refunds-v3
   4 execution    EF-00001 status=200 attempts=2 key=idem-21c7c556
   5 verification by settlement-reconciler found=1 ok=True
   6 closed       state=verified prev=b6130ffc49
  effects in the world: 1  notes: 1

3. Failure injection: execute with no permission record
  Refused: permission, idempotency_key
   1 refused      by action-executor
                missing=permission, idempotency_key
  effects in the world: 0

4. 1,000 requests, seed 7, 2% answered after the timeout
                               demo shape            v0
   answers, nothing to do             107           107
   sent to a person                     0           145
   reached the world                  893           748
     no permission record             893             0
     no policy named                  893             0
     no key for retries               893             0
     not verified by another          893             0
   duplicate effects                   14             0
   trail lines                      1,908         5,030
   broken trail links                   0             0
exit 0
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
exit 0
```

### python3 -m map.demo

```text
1. load map.yaml
   as_of 2026-11-02  today 2026-11-02  owner Daniel Price
   categories 7  options 31  claims 50  undated 0
   errors 0  warnings 8
2. options per category
   Frameworks and SDKs             7
   Hosted runtimes                 5
   Protocols                       5
   Gateways and registries         4
   Policy engines                  2
   Inference engines               4
   Evaluation and observability    4
3. options that close each gap (closes = 2 points)
   category       G1   G2   G3   G4   G5
   framework       0    0    0    0    0
   runtime         0    2    0    0    0
   protocol        0    1    1    0    0
   gateway         0    2    0    0    0
   policy          0    2    0    0    0
   inference       0    0    0    0    0
   evaluation      0    0    0    0    0
4. warnings (the map loads; a person re-reads the page)
   strands: newest claim 475 days old
   claude-managed-agents: status beta
   a2a: newest claim 235 days old
   ap2: status preview
   acp: status beta
   x402: newest claim 214 days old
   mcp-registry: status preview
   otel-genai: status development
5. shortlist at lock-in weight 1
   * LangSmith Deployment             3.0  lock-in 3
   * Amazon Bedrock AgentCore         2.5  lock-in 4
   * Gemini Enterprise Agent Runtime  2.5  lock-in 4
     Microsoft Foundry Agent Service  1.5  lock-in 4
     Claude Managed Agents            0.5  status beta
   * LangGraph                        2.5  lock-in 2
   * Microsoft Agent Framework        2.5  lock-in 2
     CrewAI                           1.5  lock-in 2
     Google ADK                       1.5  lock-in 2
     Strands Agents                   1.5  lock-in 2
     OpenAI Agents SDK                2.5  status pre-1.0
     Claude Agent SDK                 1.0  status pre-1.0
   shortlisted and stale, re-read first: 0
6. failure injection: a row with no date
   errors 2  loaded False
   refused: acme-agent-cloud claim 1: no as_of date
   refused: acme-agent-cloud: no dated claim
7. struck from the map
   OpenAI Agent Builder: deprecated 2026-06-03; shuts down 2026-11-30
map: 7 categories, 31 options; 3 runtimes and
     2 frameworks shortlisted
exit 0
```

### python3 -m baseline.demo

```text
Lakeshore baseline, corpus ops-v1, seed 2026
digest 4d42beaa56093f108a8ae2b878acd897
1. Volume: contacts are not changes
  naive units of work         14.00M  (all contacts)
  contacts                    14.00M
  contacts about a change      4.34M
  of which follow-ups          2.24M
  distinct changes             2.10M  (15.0% of contacts)
  handled by a person          61.0%
  change type              changes  person
    voluntary-rebook          330k    62%
    cancel-for-credit         300k    40%
    involuntary-rebook        260k    85%
    hotel-cancel              220k    52%
    cancel-with-refund        210k    61%
    involuntary-refund        190k    74%
    upgrade                   150k    50%
    schedule-change-accept    130k    55%
    hotel-date-change         120k    75%
    ancillary-refund           80k    62%
    car-rental-change          60k    47%
    name-correction            50k    76%
2. Cost per change, by path
  person (61% of changes)
    handle labor                 $ 31.50
    repeat contacts              $  8.40
    supervision, QA, training    $  5.60
    telephony, CRM, GDS seats    $  4.80
    error rework                 $  4.60
    total                        $ 54.90
  self-service (39% of changes)
    platform run                 $  3.10
    carrier and GDS fees         $  2.90
    payment processing           $  1.60
    abandoned attempts           $  1.90
    rework and disputes          $  1.90
    total                        $ 11.40
  blended  0.61 x 54.90 + 0.39 x 11.40 = $37.94
  annual handling cost     $79,663,500
  check: log minutes 44.2 at $42.00/h = $30.95 labor
3. Refund error, as of Oct 14, 2025
  refunds issued               0.70M
  naive: found / all           0.73%  (5,100 found)
  matured cohorts (to 2025-06-16) 0.80%
  month    refunds  found  eventual
  2024-10    56,000    500       500
  2024-11    53,200    600       600
  2024-12    58,800    460       460
  2025-01    64,400    440       440
  2025-02    51,800    400       400
  2025-03    56,000    440       440
  2025-04    57,400    560       560
  2025-05    60,200    320       320
  2025-06    63,000    520       520
  2025-07    65,800    460       460
  2025-08    60,200    360       580
  2025-09    53,200     40       320
  matured rate by carrier refund method
    email-only   1.32%
    async-batch  1.00%
    hotel        0.63%
    sync         0.58%
  involuntary refunds within 7 business days
    person       93.1%  (9,620 late)
    self-service 100.0%  (0 late)
4. Chatbot pilot, Jul to Sep 2024 (48,000 sessions)
  vendor dashboard                     54%
  verified, no person                   9%
  incidents
    PIL-1 2024-07-23  G1 output acted as a promise
    PIL-2 2024-08-08  G4 outcome stated, never verified
    PIL-3 2024-08-30  metric counted hand-offs as automated
    PIL-4 2024-09-17  G2 no permission record
  metric test on 'verified, no person'
    PASS no hand-offs, abandons or unverified counted
5. Scoreboard at baseline
  As of                      Oct 14, 2025  Daniel Price
  Changes a year                     2.1M  Marcus Bell
  Changes a month                    175k  Marcus Bell
  Agent                                0%  Ben Carter
  Assisted                             0%  Ben Carter
  Self-service                        39%  Marcus Bell
  Person                              61%  Marcus Bell
  Cost per change                  $37.94  Sarah Whitfield
  Annual handling                  $79.7M  Sarah Whitfield
  Refund error                       0.8%  Rachel Morgan
  Permission records                    0  Owen Fletcher
  Pilot incidents (2024)                4  Ben Carter
  Unauthorized actions                  0  Owen Fletcher
  Incidents (program year)              0  Ben Carter
  Cost per verified outcome           n/a  Sarah Whitfield
  Verified-outcome rate               n/a  Marcus Bell
  Duplicates                          n/a  Rachel Morgan
  p95 task latency                    n/a  Ben Carter
  Use cases                             1  Daniel Price
exit 0
```

### python3 -m method.demo

```text
1. the eight artifacts of a checkable design
   1 Scope Card       What may it do, and who owns it?
   2 Question Bank    What must be true, by plane?
   3 Estimate Sheet   How much at the worst hour, and why?
   4 Diagram          Where do control, data, evidence flow?
   5 Decision Table   Which option, on which criteria?
   6 Deep Dive        How does the riskiest step fail?
   7 Decision Record  What did we decide; what reverses it?
   8 Checklist        Does every gap have an answer and owner?
2. lint the October 6 demo, written down as a design
   artifacts present: 2 of 8
   ART 6, GAP 5, GRM 1, OWN 1
   demo: 13 findings; checklist 1 of 12 pass
3. lint v0 (Daniel Price, 2025-11-13)
   EST-1  estimate peak_requests_per_s: no assumption, no source
   DEC-1  decision durable-execution: 1 option, no alternative
   OWN-1  deep_dive approval-queue: no owner
   v0: 3 findings; checklist 9 of 12 pass
4. the estimate sheet, v0.1 (2025-11-14)
   in changes_per_year      2,100,000  changes a year
   in storm_days                    7  average days
   in window_hours                  6  hours
   in calls_per_change              6  model calls
   in tools_per_change              4  tool calls
   in refund_share               0.33  of changes
   in reviews_per_hour           30.0  per person-hour
   =  avg_per_day               5,753  changes a day
   =  storm_per_hour            6,712  changes an hour
   =  storm_per_s                1.86  changes a second
   =  peak_requests_per_s        18.6  requests a second
   =  approvals_per_hour        2,235  approvals an hour
   =  reviewers_needed           74.5  reviewers
   v0 said peak_requests_per_s = 2,000; v0.1 computes 18.6
5. sensitivity: each input at its stated low and high
   reviewers_needed (base 74.5)
     storm_days           31.9 to  106.4
     window_hours         37.3 to  111.8
     refund_share         44.7 to  100.7
   peak_requests_per_s (base 18.6)
     storm_days           7.99 to   26.6
     window_hours         9.32 to   28.0
     calls_per_change     14.9 to   29.8
6. lint v0.1
   v0.1: 0 findings; checklist 12 of 12 pass
   decision durable-execution: 3 options, chose framework loop
   records 4, 0 without a reversal condition
7. failure injection: drop the assumption on storm_days
   EST-1  estimate storm_days: no assumption
   v0.1 injected: 1 finding; checklist 11 of 12 pass
8. review checklist, v0 then v0.1
   G1 Is every action a typed proposal?            pass pass
   G2 Is permission granted outside the loop?      pass pass
   G3 Does a retry stay the same request?          pass pass
   G4 Does something that did not act verify?      pass pass
   G5 Is the business result counted?              pass pass
   M1 Has every input an assumption and source?    FAIL pass
   M2 Has every artifact a named owner?            FAIL pass
   M3 Has every decision a real alternative?       FAIL pass
   M4 Does every record say what reverses it?      pass pass
   M5 Does every evidence link resolve?            pass pass
   M6 Are all eight artifacts and questions there? pass pass
   M7 Does the diagram use only the grammar?       pass pass
method: 8 artifacts, 1 linter; v0 fails 3 checks, v0.1 passes
exit 0
```

### python3 -m planes.demo

```text
contracts: 6 declared
  C1 context         knowledge -> action
  C2 proposal           action -> control
  C3 permission        control -> gateway
  C4 effect record      action -> trail
  C5 decision record   control -> trail
  C6 verification        trail -> everyone
contract check: 0 problems
autonomy table autonomy-2026-01
  task         level             ceiling           path
  refund       act_with_approval act_with_approval assisted
  rebook       act_and_notify    act_and_notify    agent
  voucher      act_unattended    act_unattended    agent
  hotel_cancel suggest           suggest           person
autonomy check: 0 problems
replay: 800 cases, seed 6
  task          cases  done  waiting  person  unconfirmed
  refund          246   188       37      21            0
  rebook          399   331        0      67            1
  voucher         114   100        0      12            2
  hotel_cancel     41     0        0      41            0
paths: agent 431, assisted 188, person 181, unknown 0
hand-offs: sync 188 (median wait 61 s), async 181
gateway calls 622; effects in systems 619; unmediated 0
decision lines 988; trail intact True
model would have said done, not done: 181
customer told done without verification: 0
path test: 15 edges
  static: 0 path(s) skip the gateway
  probe: 3 tools, 0 acted without a permission
  result: pass
policy inside the loop: LTG-5200005 $79.60
  gateway: refused: permission from outside the loop
  effects in systems: 0
refund raised to act_and_notify: 1 problem(s)
  refund: act_and_notify above ceiling act_with_approval
voucher without a daily budget: 1 problem(s)
  voucher: unattended without limits
rebook told 'confirmed': 1 problem(s)
  rebook: customer state 'confirmed' not from the chain
levels, lowest first:
  suggest, act_with_approval, act_and_notify, act_unattended
baseline table problems: 0
exit 0
```

