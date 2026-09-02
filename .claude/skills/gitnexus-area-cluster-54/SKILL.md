---
name: gitnexus-area-cluster-54
description: "Skill for the Cluster_54 area of personal-config. 5 symbols across 1 files."
---

# Cluster_54

5 symbols | 1 files | Cohesion: 71%

## When to Use

- Understanding how _format_location, _parse_pr_number, _run_parser work
- Modifying cluster_54-related functionality

## Key Files

| File              | Symbols                                                                           |
| ----------------- | --------------------------------------------------------------------------------- |
| `pr_reference.py` | _format_location, _parse_pr_number, _run_parser, _split_repo, _validate_component |

## Key Symbols

| Symbol                | Type     | File              | Line |
| --------------------- | -------- | ----------------- | ---- |
| `_format_location`    | Function | `pr_reference.py` | 28   |
| `_parse_pr_number`    | Function | `pr_reference.py` | 63   |
| `_run_parser`         | Function | `pr_reference.py` | 70   |
| `_split_repo`         | Function | `pr_reference.py` | 44   |
| `_validate_component` | Function | `pr_reference.py` | 32   |

## Execution Flows

| Flow                                        | Type            | Steps |
| ------------------------------------------- | --------------- | ----- |
| `Main → _validate_component`                | cross_community | 8     |
| `Main → _format_location`                   | cross_community | 7     |
| `Main → _validate_component`                | cross_community | 7     |
| `Fetch_pr_info → _validate_component`       | cross_community | 5     |
| `_fetch_pr_diff_only → _validate_component` | cross_community | 4     |

## How to Explore

1. `context({name: "_format_location"})` — see callers and callees
2. `query({search_query: "cluster_54"})` — find related execution flows
3. Read key files listed above for implementation details
4. `explain({target: "<file or symbol>"})` — persisted taint findings
   (source→sink data flows), when indexed with `--pdg`
