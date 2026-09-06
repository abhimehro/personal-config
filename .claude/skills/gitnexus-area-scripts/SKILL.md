---
name: gitnexus-area-scripts
description: "Skill for the Scripts area of personal-config. 230 symbols across 20 files."
---

# Scripts

230 symbols | 20 files | Cohesion: 82%

## When to Use

- Working with code in `scripts/`
- Understanding how validate_export_action, validate_export_actions,
  validate_approval work
- Modifying scripts-related functionality

## Key Files

| File                                                         | Symbols                                                                                                                                   |
| ------------------------------------------------------------ | ----------------------------------------------------------------------------------------------------------------------------------------- |
| `scripts/pr_lifecycle_ledger.py`                             | validate_approval, validate_approved_calibration, validate_imports, validate_item, validate_item_guardrail_outcome (+52)                  |
| `scripts/pr_lifecycle_config.py`                             | validate_export_action, validate_export_actions, validate_bootstrap_pointer, validate_pointer_activation, validate_pointer_identity (+20) |
| `scripts/pr_identity.py`                                     | _bot_commit_email, _check_commit_email_signal, _comment_logins, _commit_emails, _extract_app_slug (+19)                                   |
| `media-streaming/scripts/bootstrap-jellyfin-local.py`        | _body_has_password, _encode_body, _https_required_for_credentials, _is_loopback_host, _non_loopback_allowed (+13)                         |
| `scripts/fix-recap-mdx-diff-strings.js`                      | addFixDetails, emptyFixDetails, fixMdxMapEntries, fixRecapSourcePayload, isPlainObject (+13)                                              |
| `media-streaming/archive/scripts/infuse-media-server.py`     | _get_or_generate_user, _get_or_prompt_password, main, setup_authentication, verify_rclone_remote (+9)                                     |
| `media-streaming/scripts/select-best-alldebrid-candidate.py` | apply_token_scores, clean_title, compact_token, identity_for, main (+5)                                                                   |
| `scripts/mcp_vibe_toml.py`                                   | filter_servers, load_inventory, main, profile_allowlist, render (+5)                                                                      |
| `scripts/pr_lifecycle_support.py`                            | require_https_url, require_https_urls, require_list, require_utc, require_fields (+1)                                                     |
| `adguard/scripts/create_consolidated_lists.py`               | create_denylist, extract_domains_from_file, main, print_summary, write_json_files (+1)                                                    |

## Entry Points

Start here when exploring this area:

- **`validate_export_action`** (Function) — `scripts/pr_lifecycle_config.py:314`
- **`validate_export_actions`** (Function) —
  `scripts/pr_lifecycle_config.py:309`
- **`validate_approval`** (Function) — `scripts/pr_lifecycle_ledger.py:543`
- **`validate_approved_calibration`** (Function) —
  `scripts/pr_lifecycle_ledger.py:555`
- **`validate_imports`** (Function) — `scripts/pr_lifecycle_ledger.py:620`

## Key Symbols

| Symbol                             | Type     | File                             | Line |
| ---------------------------------- | -------- | -------------------------------- | ---- |
| `validate_export_action`           | Function | `scripts/pr_lifecycle_config.py` | 314  |
| `validate_export_actions`          | Function | `scripts/pr_lifecycle_config.py` | 309  |
| `validate_approval`                | Function | `scripts/pr_lifecycle_ledger.py` | 543  |
| `validate_approved_calibration`    | Function | `scripts/pr_lifecycle_ledger.py` | 555  |
| `validate_imports`                 | Function | `scripts/pr_lifecycle_ledger.py` | 620  |
| `validate_item`                    | Function | `scripts/pr_lifecycle_ledger.py` | 84   |
| `validate_item_guardrail_outcome`  | Function | `scripts/pr_lifecycle_ledger.py` | 134  |
| `validate_item_owner`              | Function | `scripts/pr_lifecycle_ledger.py` | 139  |
| `validate_item_state`              | Function | `scripts/pr_lifecycle_ledger.py` | 125  |
| `validate_items`                   | Function | `scripts/pr_lifecycle_ledger.py` | 75   |
| `validate_known_merge_method`      | Function | `scripts/pr_lifecycle_ledger.py` | 669  |
| `validate_merge_method_entry`      | Function | `scripts/pr_lifecycle_ledger.py` | 640  |
| `validate_merge_methods`           | Function | `scripts/pr_lifecycle_ledger.py` | 631  |
| `validate_revoked_calibration`     | Function | `scripts/pr_lifecycle_ledger.py` | 574  |
| `validate_runtime_records`         | Function | `scripts/pr_lifecycle_ledger.py` | 66   |
| `validate_verified_merge_evidence` | Function | `scripts/pr_lifecycle_ledger.py` | 674  |
| `validate_verified_merge_hold`     | Function | `scripts/pr_lifecycle_ledger.py` | 679  |
| `validate_verified_merge_method`   | Function | `scripts/pr_lifecycle_ledger.py` | 663  |
| `validate_work_item_evidence`      | Function | `scripts/pr_lifecycle_ledger.py` | 615  |
| `validate_work_item_identity`      | Function | `scripts/pr_lifecycle_ledger.py` | 589  |

## Execution Flows

| Flow                                               | Type            | Steps |
| -------------------------------------------------- | --------------- | ----- |
| `Main → AdjustArrayDepth`                          | cross_community | 9     |
| `Main → IsQuoteChar`                               | cross_community | 9     |
| `Main → StepQuotedChar`                            | cross_community | 9     |
| `Main → BareArrayReplacement`                      | cross_community | 7     |
| `Main → _extract_safety_options`                   | cross_community | 6     |
| `Main → _validate_scheme`                          | cross_community | 6     |
| `Main → _validate_url_string`                      | cross_community | 6     |
| `Main → _validate_userinfo`                        | cross_community | 6     |
| `Classify_pr_identity → _mapping`                  | cross_community | 6     |
| `Classify_pr_identity → Normalize_identity_tokens` | cross_community | 6     |

## How to Explore

1. `context({name: "validate_export_action"})` — see callers and callees
2. `query({search_query: "scripts"})` — find related execution flows
3. Read key files listed above for implementation details
4. `explain({target: "<file or symbol>"})` — persisted taint findings
   (source→sink data flows), when indexed with `--pdg`
