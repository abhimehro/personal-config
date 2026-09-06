---
name: gitnexus-area-cluster-73
description: "Skill for the Cluster_73 area of personal-config. 4 symbols across 1 files."
---

# Cluster_73

4 symbols | 1 files | Cohesion: 86%

## When to Use

- Working with code in `scripts/`
- Understanding how adjustArrayDepth, advanceArrayScanState, isQuoteChar work
- Modifying cluster_73-related functionality

## Key Files

| File                                  | Symbols                                                              |
| ------------------------------------- | -------------------------------------------------------------------- |
| `scripts/lib/fix-recap-mdx-arrays.js` | adjustArrayDepth, advanceArrayScanState, isQuoteChar, stepQuotedChar |

## Key Symbols

| Symbol                  | Type     | File                                  | Line |
| ----------------------- | -------- | ------------------------------------- | ---- |
| `adjustArrayDepth`      | Function | `scripts/lib/fix-recap-mdx-arrays.js` | 36   |
| `advanceArrayScanState` | Function | `scripts/lib/fix-recap-mdx-arrays.js` | 47   |
| `isQuoteChar`           | Function | `scripts/lib/fix-recap-mdx-arrays.js` | 14   |
| `stepQuotedChar`        | Function | `scripts/lib/fix-recap-mdx-arrays.js` | 24   |

## Execution Flows

| Flow                      | Type            | Steps |
| ------------------------- | --------------- | ----- |
| `Main → AdjustArrayDepth` | cross_community | 9     |
| `Main → IsQuoteChar`      | cross_community | 9     |
| `Main → StepQuotedChar`   | cross_community | 9     |

## How to Explore

1. `context({name: "adjustArrayDepth"})` — see callers and callees
2. `query({search_query: "cluster_73"})` — find related execution flows
3. Read key files listed above for implementation details
4. `explain({target: "<file or symbol>"})` — persisted taint findings
   (source→sink data flows), when indexed with `--pdg`
