# Automated PR inventory — 2026-05-21

**Trigger:** Cursor automation cron (`0 13 * * *`).  
**Preflight:** `bash scripts/preflight-gh-pr-automation.sh --config tasks/pr-review-agent.config.yaml` — **partial FAIL** (`abhimehro/Hydrograph_Versus_Seatek_Sensors_Project` not accessible to token/app). Processed five accessible repos; Hydrograph skipped (access escalation).

**Config:** `tasks/pr-review-agent.config.yaml` — `mode: review-and-merge`, `merge_strategy: squash`, `stale_threshold_days: 30`, `auto_fix_enabled: true`.

**Open in-scope PRs (end of session):** 25

| Repo | PR | Author | Branch (head) | Category | CI | Conflicts | Age | Notes |
| --- | ---: | --- | --- | --- | --- | --- | --- | --- |
| personal-config | 1009 | abhimehro | automation/bolt-optimize-parse-inventory-api-calls | PERFORMANCE | CLEAN | none | 2026-05-21 | **ESCALATE** — touches `parse_inventory.py` (toolchain) |
| personal-config | 995 | abhimehro | cursor-agent/salvage-personal-config-939-bolt-parallelize-io | PERFORMANCE | ? | yes | 2026-05-19 | DEFER-CONFLICT (salvage batch2) |
| personal-config | 992 | abhimehro | cursor-agent/salvage-personal-config-945-testing-add-tests | CI/INFRA | ? | yes | 2026-05-19 | DEFER-CONFLICT |
| personal-config | 985 | abhimehro | cursor-agent/salvage-personal-config-938-security-fix | SECURITY | F | yes | 2026-05-19 | DEFER-CONFLICT; partial overlap with merged #1005 |
| ctrld-sync | 821 | abhimehro | cursor-agent/salvage-ctrld-sync-794-simplify-deeply-nested-logi | REFACTOR | U | ? | 2026-05-19 | DEFER — CodeScene failing; mergeability UNKNOWN after #833 merge |
| ctrld-sync | 818 | abhimehro | cursor-agent/salvage-ctrld-sync-803-retry-20260519-resume | REFACTOR | U | ? | 2026-05-19 | DEFER — `greeting` check failing |
| ctrld-sync | 815 | abhimehro | cursor-agent/salvage-ctrld-sync-806-gh-get | REFACTOR | U | ? | 2026-05-19 | DEFER — CodeScene failing |
| ctrld-sync | 789 | abhimehro | jules-17968531501053853214-4942ccca | REFACTOR | U | ? | 2026-05-14 | DEFER — `mypy` failing |
| email-security-pipeline | 867 | abhimehro | cursor-agent/salvage-email-security-pipeline-861-palette-console | SECURITY | ? | yes | 2026-05-19 | DEFER-CONFLICT (Palette salvage) |
| email-security-pipeline | 844 | abhimehro | jules-11104805255867204712-ca12f13d | REFACTOR | U | none | 2026-05-14 | DEFER — CodeScene failing |
| email-security-pipeline | 842 | abhimehro | jules-7019338312094169359-bacb924b | PERFORMANCE | U | none | 2026-05-14 | DEFER — CodeScene failing |
| email-security-pipeline | 841 | abhimehro | optimize-dict-get-4171624623426141366 | PERFORMANCE | ? | yes | 2026-05-14 | DEFER-CONFLICT |
| email-security-pipeline | 823 | abhimehro | fix-unused-imports | SECURITY | ? | yes | 2026-05-14 | DEFER-CONFLICT |
| email-security-pipeline | 807 | abhimehro | jules-15757868954206831735-437014dc | PERFORMANCE | ? | yes | 2026-05-12 | DEFER-CONFLICT |
| Seatek_Analysis | 202 | abhimehro | bolt-optimize-relpath-17705180850109355467 | PERFORMANCE | CLEAN | none | 2026-05-21 | **ESCALATE** — `.github/scripts/repository_automation_tasks.py` |
| Seatek_Analysis | 189 | abhimehro | cursor-agent/salvage-seatek-180-code-health-improv | REFACTOR | U | none | 2026-05-19 | DEFER — CodeScene queued/pending |
| Seatek_Analysis | 172 | abhimehro | bolt-fix-get-repo-info-14172787027687589562 | REFACTOR | U | none | 2026-05-14 | DEFER — CodeScene failing |
| Seatek_Analysis | 188–198 | abhimehro | cursor-agent/salvage-seatek-* | PERFORMANCE | ? | yes | 2026-05-19 | DEFER-CONFLICT — salvage batch1 (9 PRs) |
| Hydrograph_Versus_Seatek_Sensors_Project | — | — | — | — | — | — | — | **BLOCKED** — repo not accessible (preflight FAIL) |
| series_correction_project_updated | — | — | — | — | — | — | — | No open in-scope PRs |

**Merged this session (removed from open list):**

| Repo | PR | Notes |
| --- | ---: | --- |
| personal-config | 1010 | Zero-diff Jules Daily QA shell |
| ctrld-sync | 833 | Zero-diff Jules Daily QA shell |

**Previously merged (since 2026-05-20, not this session):** personal-config [#1005](https://github.com/abhimehro/personal-config/pull/1005) (CWE-78 mole salvage).
