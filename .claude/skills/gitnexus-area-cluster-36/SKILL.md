---
name: gitnexus-area-cluster-36
description: "Skill for the Cluster_36 area of personal-config. 4 symbols across 1 files."
---

# Cluster_36

4 symbols | 1 files | Cohesion: 86%

## When to Use

- Working with code in `lib/`
- Understanding how _check_ip_category, _check_ip_safety, _check_ip_set work
- Modifying cluster_36-related functionality

## Key Files

| File               | Symbols                                                        |
| ------------------ | -------------------------------------------------------------- |
| `lib/safe_http.py` | _check_ip_category, _check_ip_safety, _check_ip_set, _is_cgnat |

## Key Symbols

| Symbol               | Type     | File               | Line |
| -------------------- | -------- | ------------------ | ---- |
| `_check_ip_category` | Function | `lib/safe_http.py` | 214  |
| `_check_ip_safety`   | Function | `lib/safe_http.py` | 226  |
| `_check_ip_set`      | Function | `lib/safe_http.py` | 245  |
| `_is_cgnat`          | Function | `lib/safe_http.py` | 209  |

## Execution Flows

| Flow                                 | Type            | Steps |
| ------------------------------------ | --------------- | ----- |
| `_check_ip_set → _check_ip_category` | intra_community | 3     |
| `_check_ip_set → _is_cgnat`          | intra_community | 3     |

## How to Explore

1. `context({name: "_check_ip_category"})` — see callers and callees
2. `query({search_query: "cluster_36"})` — find related execution flows
3. Read key files listed above for implementation details
4. `explain({target: "<file or symbol>"})` — persisted taint findings
   (source→sink data flows), when indexed with `--pdg`
