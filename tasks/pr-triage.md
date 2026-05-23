# PR Triage — 2026-05-23

**Disposition key:** MERGE · MERGE-AFTER-FIX · CLOSE-DUPLICATE · CLOSE-STALE · DEFER · ESCALATE

## Phase 1 dispositions

| Repo | PR | Disposition | Rationale |
| --- | ---: | --- | --- |
| personal-config | 1026 | **MERGE** | Zero-diff QA; CodeQL/ShellCheck green (Lesson 0b exception for QA queue hygiene) |
| personal-config | 1025 | **MERGE** | Scoped perf; CI green; no trust-boundary change |
| personal-config | 1023 | **MERGE** | Sentinel CWE-74 fix across maintenance/media scripts; CI green; not `parse_inventory` / `repository_automation_tasks` |
| personal-config | 1021 | **DEFER** | Draft; 402-file salvage; CONFLICTING — Phase 2 rebuild |
| personal-config | 1020 | **DEFER** | Draft; 402-file salvage; CONFLICTING |
| personal-config | 985 | **DEFER** | Salvage secrets-path; CONFLICTING + CodeScene |
| ctrld-sync | 837 | **ESCALATE** | Required `benchmark` failing; do not merge |
| ctrld-sync | 835 | **ESCALATE** | Same benchmark infra failure |
| ctrld-sync | 821 | **MERGE** | Green CI; mergeable (merged this session) |
| ctrld-sync | 818 | **MERGE** | Merged (greeting fail non-blocking for merge API) |
| ctrld-sync | 815 | **DEFER** | CONFLICTING after sibling merges |
| ctrld-sync | 789 | **DEFER** | `mypy` failing; 8d old refactor |
| email-security-pipeline | 896 | **MERGE** | Canonical monotonic uptime change |
| email-security-pipeline | 897 | **CLOSE-DUPLICATE** | Same diff as #896; worse CI (`greeting`) |
| email-security-pipeline | 894 | **DEFER** | Draft Palette salvage; security-sensitive pipeline |
| email-security-pipeline | 841, 807 | **DEFER** | CONFLICTING; `update-branch` 422 |
| email-security-pipeline | 842, 844 | **DEFER** | CodeScene failing; pre-existing on older Bolt/Jules PRs |
| Seatek_Analysis | 172 | **MERGE** | Mergeable; CodeScene non-blocking |
| Seatek_Analysis | 204 | **DEFER** | Draft salvage #188 |
| Seatek_Analysis | 198–190 | **DEFER** | CONFLICTING salvage batch; commented for Phase 2 |
| Hydrograph_Versus_Seatek_Sensors_Project | 199 | **MERGE** | CI green; scoped pandas micro-opt |
| series_correction_project_updated | 59 | **MERGE** | CI green |
| series_correction_project_updated | 58 | **MERGE** | Cleaner Sentinel fix |
| series_correction_project_updated | 55 | **CLOSE-DUPLICATE** | Superseded by #58; scratch patch files |

## Duplicate / overlap groups

| Group | Keep | Close / defer others |
| --- | --- | --- |
| ESP monotonic uptime | #896 | #897 closed |
| Series exception leakage | #58 | #55 closed |
| ctrld-sync benchmark lane | — | #837 + #835 both blocked until benchmark fixed |

## Ready-to-execute human actions

1. **Fix ctrld-sync `benchmark` on `main`** then merge [#837](https://github.com/abhimehro/ctrld-sync/pull/837) and [#835](https://github.com/abhimehro/ctrld-sync/pull/835).
2. **Phase-2 salvage:** Rebuild `personal-config` #1020/#1021 and `Seatek_Analysis` #198–190 from current `main`.
3. **Mark ready + review** [#894](https://github.com/abhimehro/email-security-pipeline/pull/894) (Palette / trust-boundary in security pipeline).
4. Re-run `gh api -X PUT repos/.../pulls/N/update-branch` on ESP #841/#807 after next `main` merge window.

## Security escalations (no auto-merge)

- None blocking beyond standard Sentinel/Bolt review — #1023 merged after Gate 2 pass (no secrets, injection fix only).
- **email-security-pipeline** remains security-classified: defer feature/salvage PRs (#894) for human review.
