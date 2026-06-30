# PR Triage — 2026-06-30

## Duplicate & overlap groups

### ESP path traversal (media_analyzer.py)

| PR | Intent | Tests | Action |
|----|--------|-------|--------|
| **#1185** | `_is_path_traversal_attempt` + Windows drive/backslash | `tests/test_archive_path_traversal.py` | **MERGED** |
| #1187 | Similar helper, backslash normalize | none | **CLOSED** duplicate of #1185 |
| #1188 | `_is_path_traversal` variant | none | **CLOSED** duplicate of #1185 |

### ctrld Palette (main.py)

| PR | Intent | Action |
|----|--------|--------|
| #958 | `isatty()` guard on KeyboardInterrupt clear | **MERGED** first |
| #960 | Emoji display-width in `_display_len` | **MERGED** after conflict resolve on `.jules/palette.md` |

### personal-config unused-import / `__future__` cluster

Multiple Jules PRs touching the same helper scripts (`get_prs_summarize.py`, `fix-allowlist-format.py`, etc.). Merged green trivial removals (#1420, #1417, #1408, #1403, #1401, #1400, #1410, #1405, #1404). Remaining overlap deferred to salvage pass to avoid journal/test conflicts.

## Escalations

| Repo | PR | Reason |
|------|-----|--------|
| personal-config | #1430 | `automation-workflow-updates` regresses SHA pins → mutable tags (recurring Lesson 0cr) |
| email-security-pipeline | #1189 | Webhook token / alert delivery trust boundary |

## Deferred (salvage tail)

| Repo | PR | Blocker |
|------|-----|---------|
| email-security-pipeline | #1179 | CodeScene fail — `/cs-agent skill:fix-code-health-degradations` posted |
| personal-config | #1427–#1400 (subset) | Volume + overlapping test/refactor files; merge after ordering |
| personal-config | #1418, #1416 | Security-sensitive symlink / Sentinel fixes — human review |

## Stale check (30-day threshold)

No open PRs exceeded 30-day stale threshold in scanned repos.

## Merge ordering applied

1. Dependency bumps (#1181, #1429)
2. Security fix with tests (#1185) before closing dupes
3. Code-health / logging (#1171, #1170, #1186)
4. Test-only PRs (#1184, #1183)
5. Perf/UI in satellite repos (Bolt/Palette)
6. Re-validate siblings after each squash-merge (Lesson 0)
