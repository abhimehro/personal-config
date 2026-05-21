# Automated PR inventory — PR salvage workflow (2026-05-21)

**Preflight:** `bash scripts/preflight-gh-pr-automation.sh --config tasks/pr-review-agent.config.yaml` — **passed** (read-only).

**Session:** Cron salvage + cleanup (`0 17 * * *`). Live inventory from `bash scripts/get_prs.sh` after Phase-1 merges.

**Config:** `tasks/pr-review-agent.config.yaml` — `mode: review-and-merge`, `merge_strategy: squash`, `stale_threshold_days: 30`.

| Repo | Open (end) | In-scope automation PRs |
| --- | ---: | --- |
| personal-config | 4 | 3 salvage batch2 + 1 session-artifacts draft |
| ctrld-sync | 4 | 3 salvage + 1 Jules |
| email-security-pipeline | 7 | 1 draft workflow + 1 Palette salvage + 5 Jules/Bolt |
| Seatek_Analysis | 10 | 9 salvage batch1 + 1 Bolt |
| Hydrograph_Versus_Seatek_Sensors_Project | 0 | — |
| series_correction_project_updated | 1 | Sentinel |
| **Total** | **26** | |

## abhimehro/personal-config

| # | Author | Branch | Category | CI | Conflicts | Disposition (session) |
| --- | --- | --- | --- | --- | --- | --- |
| 1011 | app/cursor | cursor-agent/automated-pr-workflow-4420 | CI/INFRA | OK | CLEAN | MERGE (artifacts draft) |
| 995 | abhimehro | cursor-agent/salvage-personal-config-939-…-batch2 | PERFORMANCE | OK | DIRTY | DEFER — v2 from `main` |
| 992 | abhimehro | cursor-agent/salvage-personal-config-945-…-batch2 | CI/INFRA | OK | DIRTY | DEFER — v2 from `main` |
| 985 | abhimehro | cursor-agent/salvage-personal-config-938-…-batch2 | SECURITY | FAIL_2 | DIRTY | DEFER — v2 from `main`; overlaps merged #1005 intent |

**Resolved since 2026-05-20 inventory:** #983–#1000 (most batch2) closed or merged; [#1005](https://github.com/abhimehro/personal-config/pull/1005) **merged** on `main`; [#1009](https://github.com/abhimehro/personal-config/pull/1009) **merged** this session (parse_inventory ThreadPoolExecutor).

## abhimehro/ctrld-sync

| # | Author | Branch | Category | CI | Conflicts | Disposition |
| --- | --- | --- | --- | --- | --- | --- |
| 821 | abhimehro | cursor-agent/salvage-ctrld-sync-794-… | REFACTOR | CodeScene FAIL | none | DEFER — UNSTABLE |
| 818 | abhimehro | cursor-agent/salvage-ctrld-sync-803-… | REFACTOR | CodeScene FAIL | none | DEFER — UNSTABLE |
| 815 | abhimehro | cursor-agent/salvage-ctrld-sync-806-… | REFACTOR | CodeScene FAIL | none | DEFER — UNSTABLE |
| 789 | abhimehro | jules-17968531501053853214-… | REFACTOR | PENDING+FAIL | none | DEFER — UNSTABLE |

**Resolved since 2026-05-20:** #825, #807 merged; #824 closed superseded; #830 not in open list (may be closed).

## abhimehro/email-security-pipeline

| # | Author | Branch | Category | CI | Conflicts | Disposition |
| --- | --- | --- | --- | --- | --- | --- |
| 887 | abhimehro | automation-workflow-updates-20260521-1 | CI/INFRA | OK | CLEAN (draft) | ESCALATE — draft; touches `.github/workflows/greetings.yml` |
| 867 | abhimehro | cursor-agent/salvage-email-security-pipeline-861-… | SECURITY/UI | OK | DIRTY | DEFER — Palette salvage post-#881 |
| 844 | abhimehro | jules-11104805255867204712-… | REFACTOR | UNSTABLE | none | DEFER |
| 842 | abhimehro | jules-7019338312094169359-… | PERFORMANCE | UNSTABLE | none | DEFER |
| 841 | abhimehro | optimize-dict-get-… | PERFORMANCE | PENDING | DIRTY | DEFER |
| 823 | abhimehro | fix-unused-imports | SECURITY | PENDING | DIRTY | DEFER |
| 807 | abhimehro | jules-15757868954206831735-… | PERFORMANCE | PENDING | DIRTY | DEFER |

**Resolved this session:** [#886](https://github.com/abhimehro/email-security-pipeline/pull/886) merged; [#885](https://github.com/abhimehro/email-security-pipeline/pull/885) closed duplicate.

## abhimehro/Seatek_Analysis

| # | Author | Branch | Category | CI | Conflicts | Disposition |
| --- | --- | --- | --- | --- | --- | --- |
| 198–195, 193, 191, 190, 188 | abhimehro | cursor-agent/salvage-seatek-…-batch1 | PERFORMANCE | mostly OK | DIRTY | DEFER — batch1 cascade after #199/#175/#202 |
| 189 | abhimehro | cursor-agent/salvage-seatek-180-… | FEATURE | PENDING | none | DEFER — UNSTABLE |
| 172 | abhimehro | bolt-fix-get-repo-info-… | REFACTOR | UNSTABLE | none | DEFER |

**Resolved this session:** [#202](https://github.com/abhimehro/Seatek_Analysis/pull/202) merged (Bolt relpath hot loop).

## abhimehro/Hydrograph_Versus_Seatek_Sensors_Project

No open PRs.

## abhimehro/series_correction_project_updated

| # | Author | Branch | Category | CI | Conflicts | Disposition |
| --- | --- | --- | --- | --- | --- | --- |
| 55 | abhimehro | sentinel/fix-exception-leakage-… | SECURITY | CodeScene FAIL | none | ESCALATE — T1 Sentinel; human merge |
