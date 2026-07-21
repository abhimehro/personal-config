# PR Triage — 2026-07-20

## Duplicate / overlap

| Group | Keep | Close | Reason |
|-------|------|-------|--------|
| release-drafter 7.6.0 (pc) | #1702 | #1701 | Identical pin; prefer green twin |
| Seatek GG path-traversal | #494 | #493 | Clean history salvage (Lesson 0ee) |

## Security escalate (unchanged)

| PR | Reason |
|----|--------|
| sc #233 | Auth / session tokens |
| hg #374 | numpy 1→2 major |
| pc #1670 | Gemini + PR-automation toolchain; CONFLICTING |
| rpce #126/#127 | Tip-release artifact majors (Lesson 0dw) |

## Deferred

| PR | Reason |
|----|--------|
| ctrld #1036 | CodeScene FAIL — `/cs-agent` posted |
| rpce #132 | Style + Build shard 2 (needs macOS) |

## Merge order executed

1. Deps: pc #1702 → #1700 (after Gitleaks 503 rerun); sc #252; ctrld #1034
2. Docs/salvage: pc #1696; ctrld #1031
3. Perf/UI: pc #1704; ctrld #1037; esp #1301 → #1303 → #1304
4. Security fix: Seatek #494 (clean salvage of #493)
