# PR Triage — 2026-06-14

## Duplicate & overlap groups

### personal-config — a11y / Palette cluster

| Group | Keep | Close | Rationale |
| --- | --- | --- | --- |
| Morning Brief a11y | #1234 | #1239 | Same file (`morning-brief.py`); #1234 includes tests |
| Analytics a11y | #1242 | #1237 | #1242 superset (analytics + infuse + tests) |
| Session reports | #1238 | #1236 | #1236 CONFLICTING; #1238 newer with salvage report |

### ctrld-sync — Palette table title

| Keep | Close | Rationale |
| --- | --- | --- |
| #895 (merged) | #893 | Identical intent (CLI table title emoji alignment) |

### series_correction — Bolt vectorize

| Keep | Close | Rationale |
| --- | --- | --- |
| #119 | #114 | Both vectorize outlier detection; #119 newer/narrower |

### ctrld-sync — Content-Type perf (sequential, not duplicate)

Merge order applied: **#896** (mypy TypedDict) → **#895** (Palette) → **#892** (Bolt unroll). **#898** deferred (CodeScene) — may conflict after #892; refresh before merge.

## Infra failure on main (Lesson 0t / 0u)

| Repo | Broken check | Affected PRs | In-scope fix PR | Action |
| --- | --- | --- | --- | --- |
| personal-config | `Run All Tests` | #1243, #1242, #1234, #1235 | #1240, #1231 | **ESCALATE** toolchain restore; defer bot PRs |

**Evidence:** `repository_automation_common.py` on `main` is truncated (~42 lines); missing `from typing import Any` and module header.

## CodeScene deferrals (cs-agent posted)

| Repo | PR | Title |
| --- | ---: | --- |
| personal-config | 1240 | restore truncated automation common |
| ctrld-sync | 898 | Bolt Content-Type unroll |
| email-security-pipeline | 1109 | Palette CLI UX |
| email-security-pipeline | 1107 | ConnectionConfig salvage (draft) |
| Hydrograph | 257 | Application.process_data tests |
| series_correction | 119 | vectorize outlier detection |

## Escalation queue (human review required)

| Repo | PR | Reason |
| --- | ---: | --- |
| personal-config | 1231 | Restores `.github/scripts/*` toolchain + tasks.py |
| personal-config | 1240 | Restores truncated `repository_automation_common.py` |
| personal-config | 1235 | Touches `repository_automation_common.py` (Bolt perf) |
| email-security-pipeline | 1107 | Draft salvage — IMAP/SMTP credential refactor |
| Seatek_Analysis | 261 | CONFLICTING salvage — scanner + workflow security |

## Salvage tail (Phase 2 input)

```yaml
remainder:
  - repo: abhimehro/personal-config
    pr: 1240
    reason: toolchain_restore_blocked_codescene_and_escalation
  - repo: abhimehro/personal-config
    pr: 1231
    reason: toolchain_restore_escalation
  - repo: abhimehro/Seatek_Analysis
    pr: 261
    reason: conflicting_salvage_security_scanner
  - repo: abhimehro/email-security-pipeline
    pr: 1107
    reason: draft_connectivity_refactor_escalation
```
