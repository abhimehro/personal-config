# PR Triage — 2026-07-04

**Session:** Automated PR salvage & cleanup (cron 17:00 UTC)  
**Input:** 60 open Jules/Code Health/Bolt/Palette/Sentinel PRs across 4 active repos

## Cluster analysis

### A. Merge cascade DIRTY tail (10 PRs)

**Cause:** Lesson 0 — post-merge conflict cascade on hot files (`setup_wizard.py`, `processor.py`, `export_comparison_sheets.py`, `gh_token_env.py`) after sibling merges in the same burst.

| Cluster | PRs | Action |
|---------|-----|--------|
| `setup_wizard.py` (esp) | #1219, #1222 | DEFER → Phase 2 file-scope salvage (after #1225 landed) |
| `processor.py` / tests (sc) | #175, #177, #183, #186, #187, #189 | DEFER → Phase 2 batch salvage |
| `export_comparison_sheets.py` (sc) | #184 | **Salvaged** → draft [#195](https://github.com/abhimehro/series_correction_project_updated/pull/195) |
| `gh_token_env.py` (pc) | #1488 | **Salvaged** → draft [#1496](https://github.com/abhimehro/personal-config/pull/1496) |
| `repository_automation_common` tests (Seatek) | #405 | DEFER → Phase 2 |

### B. Duplicate / overlap closures

| Winner | Loser | Rationale |
|--------|-------|-----------|
| pc #1489 | pc #1485 | Same alldebrid script; #1485 included stray `.orig` artifact |
| pc #1494 | pc #1482 (partial) | Both touch `gh_token_env.py`; #1494 merged first; #1488 needed salvage for `gh_token_configured` |

### C. Trust-boundary deferrals (T2)

Touches PR automation toolchain — human review required per policy:

- pc [#1495](https://github.com/abhimehro/personal-config/pull/1495) — deduplicate GH token loading across `parse_inventory.py`, `run_merges.py`, etc.
- pc [#1490](https://github.com/abhimehro/personal-config/pull/1490) — tests for `run_merges.py`
- pc [#1483](https://github.com/abhimehro/personal-config/pull/1483) — `parse_inventory.py` regex perf
- pc [#1481](https://github.com/abhimehro/personal-config/pull/1481) — `.github/scripts/repository_automation_tasks.py`

### D. UNSTABLE deferrals

| PR | Failing check | Remediation |
|----|---------------|-------------|
| esp #1223 | pytest | Investigate Aho-Corasick test regression |
| esp #1215 | CodeScene | `/cs-agent skill:fix-code-health-degradations` posted |
| sc #178 | CodeScene | `/cs-agent skill:fix-code-health-degradations` posted |

### E. Superseded session artifacts

- pc #1480 (cursor session-doc draft) → closed; replaced by this run's artifacts on `cursor-agent/pr-salvage-and-cleanup-5069`

## Disposition summary

| Disposition | Count |
|-------------|------:|
| MERGE (squash) | 42 |
| CLOSE duplicate/superseded | 4 |
| SALVAGE draft opened | 2 |
| DEFER DIRTY (Phase 2 queue) | 10 |
| DEFER trust-boundary | 4 |
| DEFER UNSTABLE | 3 |

## Merge ordering applied

1. SECURITY (`sc#191`, `Seatek#412`)
2. UI / Palette (`esp#1225`)
3. Code health refactors + tests (breadth-first per repo)
4. Performance (Bolt) where non-overlapping

## Next session priorities

1. Human review: **sc [#195](https://github.com/abhimehro/series_correction_project_updated/pull/195)** (T1), **pc [#1496](https://github.com/abhimehro/personal-config/pull/1496)** (T3)
2. Batch Phase 2 salvage for **9 DIRTY** PRs on `processor.py` / `setup_wizard.py` clusters
3. Re-run Phase 1 after salvage drafts merge to clear trust-boundary cluster (#1495)
