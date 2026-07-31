# PR triage — backlog cleanup test (2026-07-30)

**Policy:** squash merge, stale_days 30, auto-fix enabled, mode review-and-merge. **No force-push.**

## Duplicate / supersede groups

| Keep (canonical) | Close as duplicate / superseded | Rationale |
| --- | --- | --- |

## Escalate / defer (no autonomous merge)

| PR | Reason |
| --- | --- |

## Outcomes

- **Executed:** 0 duplicate closures, 0 squash merges.
- **Deferred:** 0 held.
# PR Triage — 2026-07-30

## Duplicate / overlap groups

| Group | PRs | Keep | Close |
|-------|-----|------|-------|
| greetings first-interaction pin | pc #1828, #1827, #1819, #1821, #1820 | #1828 (also ai-inference pin; WI green) | #1827 (mislabeled Sentinel + journal dup) |
| rpce Set containment | #153, #151 | #153 (CI PASS) | #151 (identical, CI FAIL) |
| dummy_todos auth | series #315, #320, #330, #331 | #315 (clean auth fix) for human | #320 junk `commit_wrapper.py`; #330 import-only OK to merge first; #331 depends on max_read |
| GraphQL PR batching | pc #1820, #1821 | neither yet | #1820 has trunk binary artifacts |

## Stale (>30d)

None (all age 0–1d).

## Security / escalate

1. **pc #1822** — CORS fail-closed on archived alldebrid-server (trust boundary)
2. **pc #1827** — mislabeled; close as superseded by #1828
3. **Seatek #552** — `run_shell_command` rejects str (injection harden)
4. **series #315** — repair broken `authenticate` (auth)
5. **series #320** — auth + junk file → REQUEST_CHANGES

## Merge order (Phase 1)

1. pc #1828 (unblocks WI on main for sibling PRs)
2. series unused-import / tests: #324, #314, #317, #316, #312, #329, #330
3. Seatek tests/cleanup: #556, #559, #550, #553, #554, #563
4. rpce #153
5. Re-check WI-failing pc PRs after #1828 lands
6. pc #1819 if unique defaultdict delta remains
# PR Triage — 2026-07-30 Phase 2

## Decision rules applied

- S1: never auto-merge salvage drafts
- S2: skip journals (`.jules/*`)
- S4: adapt tests to main APIs (truncate assertion; no blind checkout)
- 0es: prefer CLEAN twin (#1831 over #1819; #153 over #151)
- 0et: surgical residuals when changed-in-both
- Auth/CORS/injection → ESCALATE only (no salvage of auth)

## Counts

| Disposition | Count |
|-------------|------:|
| CLOSE-SUPERSEDED / no-op | 8 |
| SALVAGE drafts opened | 5 |
| ESCALATE (MCP) | 3 |
| REQUEST_CHANGES | 1 (#144) |
| DEFER | 3 (#554/#563/#327) |
| Autonomous merges | **0** |

## Salvage drafts awaiting human

1. [pc #1836](https://github.com/abhimehro/personal-config/pull/1836) — GraphQL batch `run_merges` (from #1820, no trunk junk)
2. [seatek #565](https://github.com/abhimehro/Seatek_Analysis/pull/565) — automation unit tests + `flattened_updates` fix
3. [series #332](https://github.com/abhimehro/series_correction_project_updated/pull/332) — setup.py `__future__` cleanup
4. [series #333](https://github.com/abhimehro/series_correction_project_updated/pull/333) — `parse_year_pair` tests
5. [rpce #157](https://github.com/abhimehro/repoprompt-ce/pull/157) — Swift micro-opts (#146/#149/#150)

## Human T1 escalations

1. [pc #1822](https://github.com/abhimehro/personal-config/pull/1822) — CORS fail-closed
2. [seatek #552](https://github.com/abhimehro/Seatek_Analysis/pull/552) — `run_shell_command` list-only
3. [series #315](https://github.com/abhimehro/series_correction_project_updated/pull/315) — `authenticate()` repair

## Prefer Phase 1 CLEAN twins (not salvaged)

- [pc #1831](https://github.com/abhimehro/personal-config/pull/1831) — defaultdict (covers #1819)
