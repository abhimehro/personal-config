---
name: gitnexus-area-cluster-32
description: "Skill for the Cluster_32 area of personal-config. 6 symbols across 1 files."
---

# Cluster_32

6 symbols | 1 files | Cohesion: 91%

## When to Use

- Working with code in `lib/`
- Understanding how _allowed_host_set, _host_key, _is_allowed_host work
- Modifying cluster_32-related functionality

## Key Files

| File               | Symbols                                                                             |
| ------------------ | ----------------------------------------------------------------------------------- |
| `lib/safe_http.py` | _allowed_host_set, _host_key, _is_allowed_host, _is_subdomain, _normalize_host (+1) |

## Key Symbols

| Symbol              | Type     | File               | Line |
| ------------------- | -------- | ------------------ | ---- |
| `_allowed_host_set` | Function | `lib/safe_http.py` | 139  |
| `_host_key`         | Function | `lib/safe_http.py` | 122  |
| `_is_allowed_host`  | Function | `lib/safe_http.py` | 157  |
| `_is_subdomain`     | Function | `lib/safe_http.py` | 149  |
| `_normalize_host`   | Function | `lib/safe_http.py` | 111  |
| `_validate_host`    | Function | `lib/safe_http.py` | 283  |

## Execution Flows

| Flow                             | Type            | Steps |
| -------------------------------- | --------------- | ----- |
| `_validate_host → _host_key`     | intra_community | 4     |
| `_validate_host → _is_subdomain` | intra_community | 3     |

## How to Explore

1. `context({name: "_allowed_host_set"})` — see callers and callees
2. `query({search_query: "cluster_32"})` — find related execution flows
3. Read key files listed above for implementation details
4. `explain({target: "<file or symbol>"})` — persisted taint findings
   (source→sink data flows), when indexed with `--pdg`
