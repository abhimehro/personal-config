---
name: gitnexus-area-cluster-35
description: "Skill for the Cluster_35 area of personal-config. 6 symbols across 1 files."
---

# Cluster_35

6 symbols | 1 files | Cohesion: 67%

## When to Use

- Working with code in `lib/`
- Understanding how safe_download work
- Modifying cluster_35-related functionality

## Key Files

| File               | Symbols                                                                                                     |
| ------------------ | ----------------------------------------------------------------------------------------------------------- |
| `lib/safe_http.py` | _check_content_length, _check_content_type, _extract_safety_options, _write_destination, safe_download (+1) |

## Entry Points

Start here when exploring this area:

- **`safe_download`** (Function) — `lib/safe_http.py:645`

## Key Symbols

| Symbol                    | Type     | File               | Line |
| ------------------------- | -------- | ------------------ | ---- |
| `safe_download`           | Function | `lib/safe_http.py` | 645  |
| `_check_content_length`   | Function | `lib/safe_http.py` | 621  |
| `_check_content_type`     | Function | `lib/safe_http.py` | 610  |
| `_extract_safety_options` | Function | `lib/safe_http.py` | 106  |
| `_write_destination`      | Function | `lib/safe_http.py` | 634  |
| `__init__`                | Method   | `lib/safe_http.py` | 489  |

## Execution Flows

| Flow                                               | Type            | Steps |
| -------------------------------------------------- | --------------- | ----- |
| `Main → _extract_safety_options`                   | cross_community | 6     |
| `Reset_wizard_flag → _extract_safety_options`      | cross_community | 6     |
| `Process_entry → _extract_safety_options`          | cross_community | 6     |
| `Build_focus_section → _extract_safety_options`    | cross_community | 6     |
| `Build_greeting_section → _extract_safety_options` | cross_community | 6     |
| `Ensure_admin → _extract_safety_options`           | cross_community | 5     |
| `Ensure_library → _extract_safety_options`         | cross_community | 5     |
| `Wait_for_items → _extract_safety_options`         | cross_community | 5     |
| `Safe_download → _extract_safety_options`          | cross_community | 4     |
| `Safe_download → _validate_scheme`                 | cross_community | 4     |

## How to Explore

1. `context({name: "safe_download"})` — see callers and callees
2. `query({search_query: "cluster_35"})` — find related execution flows
3. Read key files listed above for implementation details
4. `explain({target: "<file or symbol>"})` — persisted taint findings
   (source→sink data flows), when indexed with `--pdg`
