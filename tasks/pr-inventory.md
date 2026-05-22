# Automated PR inventory — 2026-05-22

**Trigger:** Cursor automation cron (`0 17 * * *`) — Phase 2 salvage & cleanup.  
**Preflight:** `bash scripts/preflight-gh-pr-automation.sh --config tasks/pr-review-agent.config.yaml` — **PASS** (all 6 repos; Hydrograph now accessible, zero open PRs).  
**Config:** `tasks/pr-review-agent.config.yaml` — salvage mode (draft PRs only; no autonomous merges).

**Open in-scope PRs (end of session):** 27

| Repo | PR | Author | Branch (head) | Category | CI | Conflicts | Notes |
| --- | ---: | --- | --- | --- | --- | --- | --- |
| personal-config | 1021 | abhimehro | cursor-agent/salvage-v2-pc-995-adguard-parallel-io-a3b9 | PERFORMANCE | U | none | **NEW DRAFT** salvages closed #995 |
| personal-config | 1020 | abhimehro | cursor-agent/salvage-v2-pc-992-scratch-triage-tests-a3b9 | CI/INFRA | U | none | **NEW DRAFT** salvages closed #992 |
| personal-config | 1019 | app/cursor | cursor-agent/automated-pr-workflow-2530 | DOCS | ? | yes | Session artifact (conflicting) |
| personal-config | 985 | abhimehro | cursor-agent/salvage-personal-config-938-security-fix-20260519-pc-batch2 | SECURITY | F | yes | **ESCALATE T2** — toolchain + parse_inventory rewrite |
| ctrld-sync | 821 | abhimehro | cursor-agent/salvage-ctrld-sync-794-… | REFACTOR | U | none | DEFER — CodeScene |
| ctrld-sync | 818 | abhimehro | cursor-agent/salvage-ctrld-sync-803-… | REFACTOR | U | none | DEFER — greeting |
| ctrld-sync | 815 | abhimehro | cursor-agent/salvage-ctrld-sync-806-gh-get | REFACTOR | U | none | DEFER — CodeScene |
| ctrld-sync | 789 | abhimehro | jules-17968531501053853214-4942ccca | REFACTOR | U | none | DEFER — mypy |
| email-security-pipeline | 894 | abhimehro | cursor-agent/salvage-v2-esp-867-palette-console-a3b9 | SECURITY | U | none | **NEW DRAFT** salvages closed #867 |
| email-security-pipeline | 844 | abhimehro | jules-11104805255867204712-ca12f13d | REFACTOR | U | ? | DEFER — CodeScene |
| email-security-pipeline | 842 | abhimehro | jules-7019338312094169359-bacb924b | PERFORMANCE | U | ? | DEFER — CodeScene |
| email-security-pipeline | 841 | abhimehro | optimize-dict-get-4171624623426141366 | PERFORMANCE | ? | yes | DEFER-CONFLICT |
| email-security-pipeline | 823 | abhimehro | fix-unused-imports | SECURITY | ? | yes | DEFER-CONFLICT |
| email-security-pipeline | 807 | abhimehro | jules-15757868954206831735-437014dc | PERFORMANCE | ? | yes | DEFER-CONFLICT |
| Seatek_Analysis | 204 | abhimehro | cursor-agent/salvage-v2-seatek-188-ext-check-a3b9 | PERFORMANCE | U | none | **NEW DRAFT** salvages closed #188 |
| Seatek_Analysis | 198–190, 193, 195–197 | abhimehro | cursor-agent/salvage-seatek-*-batch1 | PERFORMANCE | OK | yes | DEFER-CONFLICT — 8 PRs (batch1 tail) |
| Seatek_Analysis | 172 | abhimehro | bolt-fix-get-repo-info-… | REFACTOR | U | none | DEFER — CodeScene |
| Hydrograph_Versus_Seatek_Sensors_Project | — | — | — | — | — | — | No open PRs |
| series_correction_project_updated | 58 | abhimehro | fix/security-exception-data-leakage-… | SECURITY | U | none | DEFER — CodeScene; prefer over #55 |
| series_correction_project_updated | 55 | abhimehro | sentinel/fix-exception-leakage-… | SECURITY | U | none | DEFER — likely duplicate of #58 |

**Closed this session (superseded by v2 salvage):**

| Repo | Old PR | New draft PR |
| --- | ---: | ---: |
| personal-config | 992 | [#1020](https://github.com/abhimehro/personal-config/pull/1020) |
| personal-config | 995 | [#1021](https://github.com/abhimehro/personal-config/pull/1021) |
| email-security-pipeline | 867 | [#894](https://github.com/abhimehro/email-security-pipeline/pull/894) |
| Seatek_Analysis | 188 | [#204](https://github.com/abhimehro/Seatek_Analysis/pull/204) |

**Auto-resolved since 2026-05-21 (dropped from queue):**

| Repo | PR | Notes |
| --- | ---: | --- |
| personal-config | 1009 | MERGED (toolchain parse_inventory parallelization) |
| personal-config | 1017 | MERGED (scratch_* parallel gh list — post-escalation) |
| Seatek_Analysis | 202 | MERGED (discover_hotspots perf) |
| Seatek_Analysis | 189 | MERGED (salvage #180) |
| email-security-pipeline | 887 | MERGED (workflow consolidation — post-escalation) |
