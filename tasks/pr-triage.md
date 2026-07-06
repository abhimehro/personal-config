# PR Triage — 2026-07-06

## Duplicate & overlap groups

### repoprompt-ce accessibility (resolved)
- **Keep:** #100 (session row buttons, 8 files)
- **Close:** #91 — subset of #100's accessibility label work

### repoprompt-ce Changelog DateFormatter (resolved)
- **Keep:** #101 (updated CI matrix, 2 files)
- **Close:** #92 — same `Changelog.swift` extraction, older branch

### personal-config locale LC_ALL (resolved)
- **Keep:** #1522 (5 files, comprehensive locale fix)
- **Close:** #1520 — subset of #1522 bin script changes
- **Close:** #1521 — comment-only reword superseded by merged locale work

### Zero-diff / no-op (resolved)
- **Close:** pc #1509, #1512, #1519 — no file changes vs base
- **Close:** Seatek #422 — daily QA summary artifact, no diff

## Security-first merge order (executed)

1. [personal-config #1507](https://github.com/abhimehro/personal-config/pull/1507) — CWE-88 osascript `--` delimiter
2. [ctrld-sync #989](https://github.com/abhimehro/ctrld-sync/pull/989) — TOCTOU cache mkdir mode
3. [series_correction #195](https://github.com/abhimehro/series_correction_project_updated/pull/195) — CLI exception output sanitization
4. Remaining green-CI PRs in dependency/perf/refactor order

## Autofix actions

| PR | Action | Outcome |
|----|--------|---------|
| pc #1526 | Merged `origin/main`; kept both bolt.md learnings | MERGED |
| sc #197 | Merged `origin/main`; kept main's security-sanitized `export_comparison_sheets.py` | MERGED |
| cs #990 | Rebased on main; updated `cache/benchmark-data.json` | benchmark still FAIL (compares vs pre-SSRF main commit `abc4e246`) |

## Deferred tail (salvage handoff)

| PR | Blocker | Recommended follow-up |
|----|---------|----------------------|
| cs #990 | `benchmark` required check — 1.89× regression from domain allowlist validation | Merge with benchmark threshold exception OR update gh-pages baseline post-merge on macOS/CI admin |
| rpce #100 | `Build and Test` + `Style` | `make dev-format` on macOS; re-run CI |
| rpce #101 | `Build and Test` + `Style` | Same as #100; likely shares Changelog formatter conflict with merged main |

## Stale check

No PRs exceeded 30-day stale threshold. All in-scope PRs were <1 day old.
