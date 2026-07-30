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
