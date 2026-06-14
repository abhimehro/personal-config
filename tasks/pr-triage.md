# PR Triage — 2026-06-13

**Mode:** salvage-and-cleanup (Phase 2)  
**Preflight:** PASS  
**Input:** Live GitHub state + deferred tail from `tasks/pr-review-2026-06-12.md`

## Triage matrix

| Disposition | Count | Action |
| --- | ---: | --- |
| SALVAGE (new draft PR) | 3 | Rebuilt from `main`, originals closed |
| CLOSE-SUPERSEDED | 5 | #886→#893, #283 on main, #278/#282 stale |
| CLOSE (original after salvage) | 3 | #1230, #1096, #1103 |
| DEFER | 8 | Infra, CodeScene, Gate 2, Phase 1 clean |
| ESCALATE T0 | 1 | personal-config #1231 infra-fix |

## Infra detection

**personal-config is infra-broken on `main`.** `repository_automation_common.py` is truncated — `DAILY_WORKFLOW_NAME` missing — causing `Run All Tests (shell + Python)` failures on unrelated PRs (#1234, #1235). Draft [#1231](https://github.com/abhimehro/personal-config/pull/1231) restores the file with green CI. **Merge #1231 before Phase 1 merges on personal-config.**

## Duplicate & overlap analysis

| Group | Keeper | Action on others | Rationale |
| --- | --- | --- | --- |
| ctrld CLI emoji alignment | **#893** | Closed #886 | Same `main.py` surface; #893 mergeable with benchmark green |
| PC analytics ARIA | **#1237** (draft) | Closed #1230 | #1230 had 15+ unrelated files; salvage is intent-only |
| Seatek shell=False | **main** | Closed #283 | `shell=False` already explicit on `main` |
| Seatek R perf (#278/#282) | — | Closed both | Branches delete tests merged since 2026-06-11 |

## Per-PR notes

### personal-config #1231 — ESCALATE T0

Restores truncated `repository_automation_common.py`. All security gates green. Human merge required before #1234/#1235 can pass tests.

### personal-config #1237 — SALVAGE (draft)

Salvages #1230 `aria-hidden` emoji spans in `analytics_dashboard.sh`. Awaiting human review.

### personal-config #1235 / #1234 — DEFER

Bolt hoist and Palette morning-brief ARIA. CI failure is **infra on base**, not PR-specific. Re-triage after #1231 merges.

### personal-config #1236 — DEFER

Phase 1 session doc draft; `DIRTY`. Superseded by this salvage session report on branch `cursor-agent/pr-salvage-and-cleanup-2e02`.

### ctrld-sync #893 / #892 — DEFER (Phase 1)

Both `MERGEABLE` with green functional CI. Route to Phase 1 review-and-merge — not salvage scope.

### email-security-pipeline #1107 / #1108 — SALVAGE (draft)

Rebuilt from `main`. Posted `/cs-agent` on #1108. Human merge required.

### Seatek_Analysis #261 — DEFER (Gate 2)

Prior salvage removed security controls (Lesson 0ci). Do not rebuild without preserving `read_file_safe` / `MAX_FILE_SIZE`.

### Hydrograph #257 / series_correction #114 — DEFER

CodeScene-only failure; cs-agent already posted. Human review after CodeScene remediation.
