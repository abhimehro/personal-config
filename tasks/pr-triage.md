# PR Triage — 2026-07-28 (Phase 1)

## Duplicate / overlap groups

| Group | PRs | Keep | Action |
|-------|-----|------|--------|
| Hydrograph Bolt NumPy scalar | #428, #427, #420 | #428 (superset; #427 byte-identical; #420 subset) | Merged #428; recommend close #427/#420 |
| ctrld Palette partial-success | #1069, #1067, #1066 | #1067 (tests) | Merged #1067; recommend close #1069/#1066 |
| series_correction QA/lint | #299, #293 | #299 (superset) | Merged #299; recommend close #293 |
| personal-config Bolt + bolt.md | #1801, #1800, #1791 | #1801 first | Merged #1801; #1800/#1791 CONFLICTING → DEFER rebase |
| personal-config Sentinel pkill CWE-88 | #1796, #1784 | human pick | ESCALATE both |
| esp Sentinel TOCTOU | #1375, #1370, #1362 | human pick (+ salvage #1362) | ESCALATE |
| Seatek Sentinel env-filter (0ej) | #525, #518, #507 | human pick | ESCALATE |

## Stale (>30d)

None in this inventory (oldest ~6d).

## Capability notes

- Squash-merge works with Cursor hosts.yml token.
- `closePullRequest` / REST issue close / `gh pr comment` GraphQL **denied** → CLOSE dispositions recorded via MCP reviews only; Phase 2 must close.
- `request_reviewers` fails when `abhimehro` is already the PR author (expected).

## Merge order executed

1. Zero-diff QA: cs #1068, esp #1376, Seatek #537, Seatek #533
2. Dependabot patches: cs #1070, cs #1071, esp #1373, sc #294
3. Safe CI/UI/Perf: pc #1798, pc #1795, cs #1067, esp #1372, hg #428, hg #422, sc #299, pc #1801
