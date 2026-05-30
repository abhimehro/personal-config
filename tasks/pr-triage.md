# PR Triage — 2026-05-30

**Session:** review-and-merge (cron `0 13 * * *`)  
**Inventory:** `tasks/pr-inventory.md`

## Duplicate / superseded groups

| Keep | Close | Rationale |
| --- | --- | --- |
| email-security-pipeline **#961** | **#960** | Identical title, same four files, same Bolt regex optimization |
| *(none — main already has QA)* | personal-config **#1094** | Zero-diff Jules Daily QA shell (Lesson 0b) |

## Disposition summary

| Disposition | Count | PRs |
| --- | ---: | --- |
| MERGE | 5 | personal-config #1091; ctrld-sync #857; email-security-pipeline #961, #963; series_correction #87 |
| CLOSE-DUPLICATE / zero-diff | 2 | personal-config #1094; email-security-pipeline #960 |
| ESCALATE | 1 | personal-config #1093 |
| DEFER | 1 | email-security-pipeline #962 |

## Gate notes

- **Gate 2 (security):** #1091 passed — no injection via string interpolation; argv-safe `osascript` pattern.
- **Trust boundary:** #1093 touches `run_merges.py` / `scratch_*` — escalated per agent policy even with green CI.
- **ESP Actions tail:** #962 fails `bandit` while pytest/CodeQL green — defer until composite action pinning is complete (extends Lesson 0u / 2026-05-29 #957 tail).

## Merge order executed

1. Security — personal-config #1091  
2. Performance — email-security-pipeline #961  
3. Hygiene — email-security-pipeline #963  
4. Performance — series_correction_project_updated #87  
5. CI/INFRA docs — ctrld-sync #857 (marked ready, then squash-merged)
