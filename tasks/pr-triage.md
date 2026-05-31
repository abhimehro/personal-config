# PR Triage — 2026-05-31

**Session:** Automated PR review (cron `0 13 * * *`)  
**Stale threshold:** 30 days (none in-scope exceeded)

## Duplicate & overlap analysis

| Group | Keep | Close / defer others | Rationale |
| --- | --- | --- | --- |
| Bolt scratch perf | **#1100** (merged) | **#1093** (defer, conflicting) | Same `scratch_inventory.py` tuple change; #1093 adds `run_merges.py` (toolchain) |
| Jules Daily QA | **#1101** (merged) | — | Zero-diff queue hygiene |

No semantic duplicates across repos. No stale (>30d) in-scope PRs.

## Per-PR disposition

| Repo | PR | Category | Disposition | Gates |
| --- | ---: | --- | --- | --- |
| personal-config | 1098 | SECURITY | **MERGE** | G1–G3 pass; CWE-74 fix validated |
| personal-config | 1097 | UI | **MERGE** | G1–G3 pass; demo-only scope |
| personal-config | 1100 | PERFORMANCE | **MERGE** | G1–G3 pass; scratch helper only |
| personal-config | 1101 | CI/INFRA | **MERGE** | Zero-diff; required checks green |
| ctrld-sync | 860 | CI/INFRA | **MERGE** | Docs-only QA notes |
| personal-config | 1093 | PERFORMANCE | **DEFER** | G4 trust boundary (`run_merges.py`); conflict after #1100 |
| personal-config | 1096 | CI/INFRA | **DEFER** | Draft; `tasks/pr-*` toolchain docs |
| email-security-pipeline | 966 | CI/INFRA | **ESCALATE** | G1 fail (bandit); G2 fail (unpins actions) |

## Security notes

- **#1098:** Legitimate injection hardening; no privilege escalation.
- **#966:** Regresses SHA pinning policy; must not merge until workflows use full commit SHAs throughout (including nested composite actions — Lesson 0y).

## Merge order executed

1. Security (#1098)  
2. UI (#1097)  
3. Performance scratch (#1100)  
4. Zero-diff QA (#1101)  
5. ctrld-sync QA docs (#860)
