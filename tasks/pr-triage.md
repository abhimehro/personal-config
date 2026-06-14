# PR Triage — 2026-06-14

**Mode:** salvage-and-cleanup (Phase 2)  
**Preflight:** PASS  
**Input:** Live GitHub state + deferred tail from `tasks/pr-review-2026-06-13.md`

## Triage matrix

| Disposition | Count | Action |
| --- | ---: | --- |
| SALVAGE (new draft PR) | 1 | ctrld #898 → #899 |
| CLOSE-SUPERSEDED / DUPLICATE | 5 | #1231→#1240, #1245→#1242, #1109→#1112, #1244 session doc |
| CLOSE (Gate 2 security) | 1 | Seatek #261 |
| DEFER (Phase 1 / human merge) | 9 | See remainder below |
| ESCALATE T0 | 1 | personal-config #1240 infra-fix |

## Infra detection

**personal-config `main` is still infra-broken.** `repository_automation_common.py` lacks `from typing import Any`, causing `NameError` on unrelated PR test runs (#1243, #1245, #1234, #1235). Draft [#1240](https://github.com/abhimehro/personal-config/pull/1240) restores the module with green security CI. Closed duplicate [#1231](https://github.com/abhimehro/personal-config/pull/1231). **Human merge #1240 before Phase 1 burst.**

## Duplicate & overlap analysis

| Group | Keeper | Closed | Rationale |
| --- | --- | --- | --- |
| PC infra-fix drafts | **#1240** | #1231 | Same restore intent; #1240 newer with cs-agent remediation |
| PC analytics ARIA | **#1242** | #1245, #1237 (prior) | #1242 is superset (dashboard + infuse + tests) |
| ESP terminal color reset | **#1112** | #1109 | Same files; #1112 newer |
| ctrld Content-Type unroll | **#899** (salvage) | #898 | #898 DIRTY after #892 merge |

## Per-PR notes

### personal-config #1240 — ESCALATE T0

Single infra-fix draft after closing #1231. All security gates green. Unblocks `Run All Tests` on Bolt/Palette PRs once merged.

### ctrld-sync #899 — SALVAGE (draft)

Rebuilt Content-Type unroll from #898 on current `main`. Local `uv run pytest` — 341 passed. `/cs-agent` posted; awaiting CodeScene.

### Seatek_Analysis #261 — CLOSE (Gate 2)

`DIRTY` and would delete `read_file_safe` / `MAX_FILE_SIZE` vs current `main`. Lesson 0ci applies — do not salvage without preserving security controls.

### email-security-pipeline #1107 — DEFER

Prior salvage from 2026-06-13; all functional CI green. Awaiting human merge.

### email-security-pipeline #1111 / #1112 — DEFER (Phase 1)

Both CLEAN/UNSTABLE with green pytest/bandit. #1111 is broad Jules QA formatting; #1112 is focused Palette terminal reset.

### Hydrograph #257 / series_correction #119 — DEFER

CodeScene-only failures; `/cs-agent` already posted on both. #119 replaced closed #114.

### personal-config #1234 / #1235 / #1242 / #1243 — DEFER (Phase 1)

MERGEABLE but `Run All Tests` fails on truncated `main` base — not PR-specific. Re-triage after #1240 merges.
