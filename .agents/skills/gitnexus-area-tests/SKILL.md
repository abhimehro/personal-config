---
name: gitnexus-area-tests
description: "Skill for the Tests area of personal-config. 451 symbols across 50 files."
---

# Tests

451 symbols | 50 files | Cohesion: 84%

## When to Use

- Working with code in `tests/`
- Understanding how validate_url, run_gh, clear_gh_token_cache work
- Modifying tests-related functionality

## Key Files

| File                                      | Symbols                                                                                                                                                                                                                                                |
| ----------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| `tests/test_parse_inventory.py`           | _build_info, _recent_iso, test_get_pr_category_conflicting_dirty, test_get_pr_category_conflicting_explicit, test_get_pr_category_none_recent_clean_failing (+30)                                                                                      |
| `tests/test_safe_http.py`                 | test_allowed_hosts_exact, test_allowed_hosts_subdomain, test_allowed_hosts_with_port, test_cgnat_blocked, test_ipv4_mapped_loopback_blocked (+23)                                                                                                      |
| `tests/test_pr_lifecycle_artifacts.py`    | test_acknowledgement_and_cancellation_do_not_increment_revision, test_calibration_approval_passes_with_seven_current_events, test_main_pointer_cannot_be_used_as_runtime_ledger, test_nonempty_example_and_source_exports_validate, write_ledger (+22) |
| `tests/test_extract_domains.py`           | test_empty_rules, test_happy_path, test_invalid_json, test_missing_file, test_missing_rules (+20)                                                                                                                                                      |
| `tests/test_consolidate_adblock_lists.py` | test_empty_domains, test_happy_path, test_invalid_input_types, test_json_serialization_safety, test_single_domain (+20)                                                                                                                                |
| `tests/test_detect_duplicates.py`         | test_group_prs_by_files_api_failure, test_group_prs_by_files_empty_files, test_group_prs_by_files_empty_input, test_group_prs_by_files_happy_path, test_group_prs_by_files_skips_invalid_reference (+17)                                               |
| `tests/test_gh_token_env.py`              | _write_secure_env_file, setUp, test_cache_reset_isolation, test_env_var_takes_precedence_over_file, test_load_rejects_file_not_owned_by_current_user (+15)                                                                                             |
| `tests/test_pr_reference.py`              | test_from_parts, test_pr_leading_hyphen, test_pr_leading_zero, test_pr_negative, test_pr_non_decimal (+15)                                                                                                                                             |
| `tests/test_get_prs_summarize.py`         | test_author_is_bot, test_body_markers, test_bot_login_suffix, test_branch_signals, test_human_pr (+12)                                                                                                                                                 |
| `lib/safe_http.py`                        | _parse_addr_entry, _parse_addr_info, _resolve_ips, _resolve_port, _validate_scheme (+11)                                                                                                                                                               |

## Entry Points

Start here when exploring this area:

- **`validate_url`** (Function) — `lib/safe_http.py:291`
- **`run_gh`** (Function) — `detect_duplicates.py:10`
- **`clear_gh_token_cache`** (Function) — `gh_token_env.py:177`
- **`load_gh_token_env`** (Function) — `gh_token_env.py:157`
- **`fetch_details`** (Function) — `scripts/get_prs_summarize.py:169`

## Key Symbols

| Symbol                      | Type     | File                                           | Line |
| --------------------------- | -------- | ---------------------------------------------- | ---- |
| `validate_url`              | Function | `lib/safe_http.py`                             | 291  |
| `run_gh`                    | Function | `detect_duplicates.py`                         | 10   |
| `clear_gh_token_cache`      | Function | `gh_token_env.py`                              | 177  |
| `load_gh_token_env`         | Function | `gh_token_env.py`                              | 157  |
| `fetch_details`             | Function | `scripts/get_prs_summarize.py`                 | 169  |
| `safe_request`              | Function | `lib/safe_http.py`                             | 411  |
| `extract_horoscope_text`    | Function | `scripts/morning-brief/morning-brief.py`       | 671  |
| `automation_hints`          | Function | `scripts/get_prs_summarize.py`                 | 84   |
| `check_summary`             | Function | `scripts/get_prs_summarize.py`                 | 28   |
| `validate_schema`           | Function | `scripts/pr_lifecycle_schema.py`               | 11   |
| `validate`                  | Function | `scripts/pr_lifecycle_validation.py`           | 17   |
| `load_yaml`                 | Function | `scripts/pr_lifecycle_yaml.py`                 | 35   |
| `main`                      | Function | `scripts/validate_pr_lifecycle_artifacts.py`   | 15   |
| `extract_domains_from_file` | Function | `adguard/scripts/extract_domains.py`           | 19   |
| `create_json_structure`     | Function | `adguard/scripts/consolidate_adblock_lists.py` | 101  |
| `write_json_files`          | Function | `adguard/scripts/consolidate_adblock_lists.py` | 112  |
| `load_json_file`            | Function | `adguard/scripts/consolidate_adblock_lists.py` | 17   |
| `rewrite_triage_file`       | Function | `detect_duplicates.py`                         | 190  |
| `format_lists`              | Function | `generate_report.py`                           | 43   |
| `get_category`              | Function | `scratch_inventory.py`                         | 124  |

## Execution Flows

| Flow                                     | Type            | Steps |
| ---------------------------------------- | --------------- | ----- |
| `Main → Parse_env_line`                  | cross_community | 9     |
| `Main → _validate_env_fd`                | cross_community | 8     |
| `Main → _validate_component`             | cross_community | 8     |
| `_fetch_pr_diff_only → Parse_env_line`   | cross_community | 8     |
| `Main → Resolve_gh_token_env_file`       | cross_community | 7     |
| `Main → _format_location`                | cross_community | 7     |
| `_fetch_pr_diff_only → _validate_env_fd` | cross_community | 7     |
| `Main → _validate_component`             | cross_community | 7     |
| `Fetch_pr_info → Parse_env_line`         | cross_community | 7     |
| `_categorize_pr_task → Parse_env_line`   | cross_community | 7     |

## How to Explore

1. `context({name: "validate_url"})` — see callers and callees
2. `query({search_query: "tests"})` — find related execution flows
3. Read key files listed above for implementation details
4. `explain({target: "<file or symbol>"})` — persisted taint findings
   (source→sink data flows), when indexed with `--pdg`
