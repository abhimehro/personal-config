---
name: gitnexus-area-cluster-38
description: "Skill for the Cluster_38 area of personal-config. 4 symbols across 1 files."
---

# Cluster_38

4 symbols | 1 files | Cohesion: 86%

## When to Use

- Working with code in `lib/`
- Understanding how redirect_request work
- Modifying cluster_38-related functionality

## Key Files

| File               | Symbols                                                               |
| ------------------ | --------------------------------------------------------------------- |
| `lib/safe_http.py` | _filter_headers, _is_allowed_scheme, _redirect_body, redirect_request |

## Entry Points

Start here when exploring this area:

- **`redirect_request`** (Method) — `lib/safe_http.py:493`

## Key Symbols

| Symbol               | Type     | File               | Line |
| -------------------- | -------- | ------------------ | ---- |
| `redirect_request`   | Method   | `lib/safe_http.py` | 493  |
| `_filter_headers`    | Function | `lib/safe_http.py` | 472  |
| `_is_allowed_scheme` | Function | `lib/safe_http.py` | 457  |
| `_redirect_body`     | Function | `lib/safe_http.py` | 464  |

## Execution Flows

| Flow                                         | Type            | Steps |
| -------------------------------------------- | --------------- | ----- |
| `Redirect_request → _extract_safety_options` | cross_community | 3     |
| `Redirect_request → _validate_scheme`        | cross_community | 3     |
| `Redirect_request → _validate_url_string`    | cross_community | 3     |
| `Redirect_request → _validate_userinfo`      | cross_community | 3     |

## How to Explore

1. `context({name: "redirect_request"})` — see callers and callees
2. `query({search_query: "cluster_38"})` — find related execution flows
3. Read key files listed above for implementation details
4. `explain({target: "<file or symbol>"})` — persisted taint findings
   (source→sink data flows), when indexed with `--pdg`
