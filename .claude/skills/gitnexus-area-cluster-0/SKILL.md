---
name: gitnexus-area-cluster-0
description: "Skill for the Cluster_0 area of personal-config. 3 symbols across 1 files."
---

# Cluster_0

3 symbols | 1 files | Cohesion: 100%

## When to Use

- Working with code in `lib/`
- Understanding how TooManyRedirectsError, UnsafeRedirectError, UnsafeURLError
  work
- Modifying cluster_0-related functionality

## Key Files

| File               | Symbols                                                    |
| ------------------ | ---------------------------------------------------------- |
| `lib/safe_http.py` | TooManyRedirectsError, UnsafeRedirectError, UnsafeURLError |

## Entry Points

Start here when exploring this area:

- **`TooManyRedirectsError`** (Class) — `lib/safe_http.py:78`
- **`UnsafeRedirectError`** (Class) — `lib/safe_http.py:74`
- **`UnsafeURLError`** (Class) — `lib/safe_http.py:70`

## Key Symbols

| Symbol                  | Type  | File               | Line |
| ----------------------- | ----- | ------------------ | ---- |
| `TooManyRedirectsError` | Class | `lib/safe_http.py` | 78   |
| `UnsafeRedirectError`   | Class | `lib/safe_http.py` | 74   |
| `UnsafeURLError`        | Class | `lib/safe_http.py` | 70   |

## How to Explore

1. `context({name: "TooManyRedirectsError"})` — see callers and callees
2. `query({search_query: "cluster_0"})` — find related execution flows
3. Read key files listed above for implementation details
4. `explain({target: "<file or symbol>"})` — persisted taint findings
   (source→sink data flows), when indexed with `--pdg`
