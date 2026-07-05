# PR Triage — 2026-07-05

**Session:** Automated PR review & cleanup (cron 13:00 UTC)  
**Mode:** review-and-merge

## Duplicate & overlap analysis

| Group | PRs | Decision | Rationale |
|-------|-----|----------|-----------|
| GH token dedup | pc #1495, #1496 | Merge #1496; close #1495 | #1496 is narrower salvage already green; #1495 became DIRTY after perf merges |
| ESP setup wizard refactor | esp #1215, #1219, #1222 | Merge #1215; close #1219/#1222 | #1215 umbrella QA merge; siblings DIRTY |
| ctrld Palette TTY | cs #979, #981 | Merge both sequentially | #981 conflicted after #979; resolved via merge-main + `_clear_current_line()` |
| sc bot backlog | #175–#189 (7 DIRTY) | Close all | Stale conflicts from burst; reopen from fresh main if needed |
| Session doc | pc #1497 | Close | Superseded by this session report |

## Security gate review

| PR | Gate | Result |
|----|------|--------|
| hg #320 | Path traversal in config-driven `data_dir` | **MERGE** — Sentinel fix, CI green |
| Seatek #418 | `subprocess.run` shell=False | **MERGE** — CI green |
| pc #1500 | pgrep option injection (CWE-88) | **MERGE-AFTER-FIX** — merged main to fix unrelated pytest import CI failure |
| sc #195 | CLI exception output sanitization | **DEFER** — CodeScene red; cs-agent posted |

## CI triage notes

- **pc #1500:** Initial FAIL was `test_refactoring_agent_workflow` importing `pytest` on branch stale vs main. Merging `main` fixed CI; security diff unchanged.
- **cs #981:** Became DIRTY after #979 squash-merge; conflict resolution kept `_clear_current_line()` helper.
- **rpce #91/#92:** Style job fails; Build and Test pass. Cloud Linux agent cannot install SwiftFormat (Homebrew required).

## Disposition summary

| Disposition | Count |
|-------------|-------|
| MERGE | 13 |
| MERGE-AFTER-FIX | 2 (#1500, #981) |
| CLOSE-DUPLICATE/SUPERSEDED | 12 |
| DEFER (CodeScene) | 2 |
| DEFER (Style/macOS tooling) | 2 |

## Next session priorities

1. Re-check sc #195 / #178 after CodeScene cs-agent run completes.
2. Salvage or close rpce #91/#92 after macOS `make dev-format` pass.
3. Monitor for new bot PR burst on `series_correction_project_updated` after backlog close.
