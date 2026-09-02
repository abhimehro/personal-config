---
name: gitnexus-area-cluster-74
description: "Skill for the Cluster_74 area of personal-config. 4 symbols across 1 files."
---

# Cluster_74

4 symbols | 1 files | Cohesion: 75%

## When to Use

- Working with code in `scripts/`
- Understanding how bareArrayReplacement, findMatchingArrayEnd,
  fixBareArrayAttrs work
- Modifying cluster_74-related functionality

## Key Files

| File                                  | Symbols                                                                            |
| ------------------------------------- | ---------------------------------------------------------------------------------- |
| `scripts/lib/fix-recap-mdx-arrays.js` | bareArrayReplacement, findMatchingArrayEnd, fixBareArrayAttrs, rewriteOneBareArray |

## Key Symbols

| Symbol                 | Type     | File                                  | Line |
| ---------------------- | -------- | ------------------------------------- | ---- |
| `bareArrayReplacement` | Function | `scripts/lib/fix-recap-mdx-arrays.js` | 90   |
| `findMatchingArrayEnd` | Function | `scripts/lib/fix-recap-mdx-arrays.js` | 68   |
| `fixBareArrayAttrs`    | Function | `scripts/lib/fix-recap-mdx-arrays.js` | 127  |
| `rewriteOneBareArray`  | Function | `scripts/lib/fix-recap-mdx-arrays.js` | 103  |

## Execution Flows

| Flow                          | Type            | Steps |
| ----------------------------- | --------------- | ----- |
| `Main → AdjustArrayDepth`     | cross_community | 9     |
| `Main → IsQuoteChar`          | cross_community | 9     |
| `Main → StepQuotedChar`       | cross_community | 9     |
| `Main → BareArrayReplacement` | cross_community | 7     |

## How to Explore

1. `context({name: "bareArrayReplacement"})` — see callers and callees
2. `query({search_query: "cluster_74"})` — find related execution flows
3. Read key files listed above for implementation details
4. `explain({target: "<file or symbol>"})` — persisted taint findings
   (source→sink data flows), when indexed with `--pdg`
