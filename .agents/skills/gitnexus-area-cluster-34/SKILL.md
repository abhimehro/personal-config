---
name: gitnexus-area-cluster-34
description: "Skill for the Cluster_34 area of personal-config. 5 symbols across 1 files."
---

# Cluster_34

5 symbols | 1 files | Cohesion: 53%

## When to Use

- Working with code in `lib/`
- Understanding how safe_urlopen work
- Modifying cluster_34-related functionality

## Key Files

| File               | Symbols                                                                              |
| ------------------ | ------------------------------------------------------------------------------------ |
| `lib/safe_http.py` | _build_safe_opener, _collapse_timeout, _make_safe_response, _read_body, safe_urlopen |

## Entry Points

Start here when exploring this area:

- **`safe_urlopen`** (Function) — `lib/safe_http.py:574`

## Key Symbols

| Symbol                | Type     | File               | Line |
| --------------------- | -------- | ------------------ | ---- |
| `safe_urlopen`        | Function | `lib/safe_http.py` | 574  |
| `_build_safe_opener`  | Function | `lib/safe_http.py` | 536  |
| `_collapse_timeout`   | Function | `lib/safe_http.py` | 529  |
| `_make_safe_response` | Function | `lib/safe_http.py` | 562  |
| `_read_body`          | Function | `lib/safe_http.py` | 550  |

## Execution Flows

| Flow                                          | Type            | Steps |
| --------------------------------------------- | --------------- | ----- |
| `Main → _extract_safety_options`              | cross_community | 6     |
| `Main → _validate_scheme`                     | cross_community | 6     |
| `Main → _validate_url_string`                 | cross_community | 6     |
| `Main → _validate_userinfo`                   | cross_community | 6     |
| `Reset_wizard_flag → _extract_safety_options` | cross_community | 6     |
| `Reset_wizard_flag → _validate_scheme`        | cross_community | 6     |
| `Reset_wizard_flag → _validate_url_string`    | cross_community | 6     |
| `Reset_wizard_flag → _validate_userinfo`      | cross_community | 6     |
| `Main → _build_safe_opener`                   | cross_community | 5     |
| `Main → _collapse_timeout`                    | cross_community | 5     |

## How to Explore

1. `context({name: "safe_urlopen"})` — see callers and callees
2. `query({search_query: "cluster_34"})` — find related execution flows
3. Read key files listed above for implementation details
4. `explain({target: "<file or symbol>"})` — persisted taint findings
   (source→sink data flows), when indexed with `--pdg`
