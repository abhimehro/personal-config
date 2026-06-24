# PR Inventory — 2026-06-24

**Preflight:** PASS (6/6 configured repos; repoprompt-ce checked ad hoc)\
**Phase 2:** cron `0 17 * * *` — salvage-and-cleanup (`cursor-agent/pr-salvage-and-cleanup-f450`)\
**Config:** `tasks/pr-review-agent.config.yaml`

## Scope summary

| Repo | Open at start | Closed dup/stale | Salvage drafts | Escalated | Deferred EOD | Open EOD |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| personal-config | 10 | 0 | 0 | 0 | 10 | 10 |
| ctrld-sync | 5 | 0 | 0 | 0 | 0 | 5 |
| email-security-pipeline | 2 | 0 | 0 | 0 | 0 | 2 |
| Seatek_Analysis | 1 | 0 | 0 | 0 | 0 | 1 |
| Hydrograph_Versus_Seatek_Sensors_Project | 1 | 0 | 0 | 0 | 1 | 1 |
| series_correction_project_updated | 1 | 0 | 0 | 0 | 0 | 1 |
| repoprompt-ce | 12 | 3 | 0 | 0 | 9 | 9 |

**Totals:** 32 PRs inventoried · 0 merges · 3 closes · 0 salvage drafts · 0 escalations opened · 20 deferred

## Conflict queue

**0 DIRTY / CONFLICTING PRs** at session start. All open PRs are `MERGEABLE`.

## Full inventory at session start

| Repo | PR | Author | Category | Merge | CI | Age | Disposition |
| --- | ---: | --- | --- | --- | --- | ---: | --- |
| personal-config | [#1343](https://github.com/abhimehro/personal-config/pull/1343) | dependabot | DEPENDENCY | MERGEABLE | Codacy fail | 0 | **DEFER** (main infra) |
| personal-config | [#1340](https://github.com/abhimehro/personal-config/pull/1340) | abhimehro (Palette) | UI | MERGEABLE | Codacy fail | 1 | **DEFER** |
| personal-config | [#1339](https://github.com/abhimehro/personal-config/pull/1339) | app/cursor | CI/INFRA | MERGEABLE | Codacy fail | 1 | **DEFER** (session draft) |
| personal-config | [#1338](https://github.com/abhimehro/personal-config/pull/1338) | app/cursor | CI/INFRA | MERGEABLE | Codacy fail | 1 | **DEFER** (session draft) |
| personal-config | [#1337](https://github.com/abhimehro/personal-config/pull/1337) | abhimehro (Bolt) | PERFORMANCE | MERGEABLE | Codacy fail | 1 | **DEFER** |
| personal-config | [#1336](https://github.com/abhimehro/personal-config/pull/1336) | abhimehro (Bolt) | PERFORMANCE | MERGEABLE | Codacy fail | 1 | **DEFER** |
| personal-config | [#1334](https://github.com/abhimehro/personal-config/pull/1334) | abhimehro (automation) | CI/INFRA | MERGEABLE | Codacy fail | 1 | **DEFER** |
| personal-config | [#1333](https://github.com/abhimehro/personal-config/pull/1333) | dependabot | DEPENDENCY | MERGEABLE | Codacy fail | 1 | **DEFER** |
| personal-config | [#1332](https://github.com/abhimehro/personal-config/pull/1332) | dependabot | DEPENDENCY | MERGEABLE | Codacy fail | 1 | **DEFER** |
| personal-config | [#1330](https://github.com/abhimehro/personal-config/pull/1330) | dependabot | DEPENDENCY | MERGEABLE | Codacy fail | 1 | **DEFER** |
| ctrld-sync | [#942](https://github.com/abhimehro/ctrld-sync/pull/942) | dependabot | DEPENDENCY | CLEAN | green | 2 | **MERGE** (Phase 1) |
| ctrld-sync | [#941](https://github.com/abhimehro/ctrld-sync/pull/941) | dependabot | DEPENDENCY | CLEAN | green | 2 | **MERGE** (Phase 1) |
| ctrld-sync | [#940](https://github.com/abhimehro/ctrld-sync/pull/940) | dependabot | DEPENDENCY | CLEAN | green | 2 | **MERGE** (Phase 1) |
| ctrld-sync | [#939](https://github.com/abhimehro/ctrld-sync/pull/939) | dependabot | DEPENDENCY | CLEAN | green | 2 | **MERGE** (Phase 1) |
| ctrld-sync | [#938](https://github.com/abhimehro/ctrld-sync/pull/938) | dependabot | DEPENDENCY | CLEAN | green | 2 | **MERGE** (Phase 1) |
| email-security-pipeline | [#1147](https://github.com/abhimehro/email-security-pipeline/pull/1147) | dependabot | DEPENDENCY | CLEAN | green | 1 | **MERGE** (Phase 1) |
| email-security-pipeline | [#1146](https://github.com/abhimehro/email-security-pipeline/pull/1146) | dependabot | DEPENDENCY | CLEAN | green | 1 | **MERGE** (Phase 1) |
| Seatek_Analysis | [#360](https://github.com/abhimehro/Seatek_Analysis/pull/360) | dependabot | DEPENDENCY | CLEAN | green | 1 | **MERGE** (Phase 1) |
| Hydrograph_Versus_Seatek_Sensors_Project | [#292](https://github.com/abhimehro/Hydrograph_Versus_Seatek_Sensors_Project/pull/292) | dependabot | DEPENDENCY | MERGEABLE | submit-pypi fail | 1 | **DEFER** |
| series_correction_project_updated | [#149](https://github.com/abhimehro/series_correction_project_updated/pull/149) | dependabot | DEPENDENCY | CLEAN | green | 0 | **MERGE** (Phase 1) |
| repoprompt-ce | [#52](https://github.com/abhimehro/repoprompt-ce/pull/52) | abhimehro (Bolt) | PERFORMANCE | MERGEABLE | Style fail | 0 | **DEFER** |
| repoprompt-ce | [#51](https://github.com/abhimehro/repoprompt-ce/pull/51) | abhimehro (Palette) | UI | MERGEABLE | Style fail | 1 | **DEFER** |
| repoprompt-ce | [#50](https://github.com/abhimehro/repoprompt-ce/pull/50) | abhimehro (Jules) | CI/INFRA | MERGEABLE | Style fail | 1 | **DEFER** |
| repoprompt-ce | [#49](https://github.com/abhimehro/repoprompt-ce/pull/49) | abhimehro (Bolt) | PERFORMANCE | MERGEABLE | Style fail | 1 | **CLOSE-DUPLICATE** → #52 |
| repoprompt-ce | [#46](https://github.com/abhimehro/repoprompt-ce/pull/46) | dependabot | DEPENDENCY | MERGEABLE | Style fail | 2 | **DEFER** |
| repoprompt-ce | [#45](https://github.com/abhimehro/repoprompt-ce/pull/45) | dependabot | DEPENDENCY | MERGEABLE | Style fail | 2 | **DEFER** |
| repoprompt-ce | [#44](https://github.com/abhimehro/repoprompt-ce/pull/44) | dependabot | DEPENDENCY | MERGEABLE | Style fail | 2 | **DEFER** |
| repoprompt-ce | [#43](https://github.com/abhimehro/repoprompt-ce/pull/43) | dependabot | DEPENDENCY | MERGEABLE | Style fail | 2 | **DEFER** |
| repoprompt-ce | [#42](https://github.com/abhimehro/repoprompt-ce/pull/42) | dependabot | DEPENDENCY | MERGEABLE | Style fail | 2 | **DEFER** |
| repoprompt-ce | [#41](https://github.com/abhimehro/repoprompt-ce/pull/41) | abhimehro (salvage) | SECURITY | MERGEABLE | Style fail | 2 | **DEFER** (T1) |
| repoprompt-ce | [#25](https://github.com/abhimehro/repoprompt-ce/pull/25) | abhimehro (salvage) | UI | MERGEABLE | Style fail | 4 | **CLOSE-DUPLICATE** → #51 |
| repoprompt-ce | [#24](https://github.com/abhimehro/repoprompt-ce/pull/24) | abhimehro (salvage) | CI/INFRA | MERGEABLE | Style fail | 4 | **CLOSE-DUPLICATE** → #50 |

## Phase 2 reconciliation (prior tail)

| Prior tail PR | Outcome |
| --- | --- |
| pc #1311 (T0 infra-fix) | **MERGED** on `main` |
| rp #29 (T0 infra-fix) | **MERGED** on `main` |
| ctrld #943 (T0) | **MERGED** on `main` |
| rp #28 (Keychain v2) | **CLOSED** — superseded by #41 |
| sc #135, #144 | **CLOSED** — prior perf/format tails resolved |

## Open at session end

| Repo | PR | Tier | Reason |
| --- | ---: | --- | --- |
| personal-config | all 10 open | T0 | Codacy Security Scan failing across queue — suspected `main` infra |
| ctrld-sync | #938–#942 | T3 | CLEAN dependabot cluster — Phase 1 merge candidates |
| email-security-pipeline | #1146, #1147 | T3 | CLEAN dependabot — Phase 1 merge candidates |
| Seatek_Analysis | #360 | T3 | CLEAN dependabot — Phase 1 merge candidate |
| series_correction | #149 | T3 | CLEAN dependabot — Phase 1 merge candidate |
| Hydrograph | #292 | T3 | `submit-pypi` check failing |
| repoprompt-ce | #41 | T1 | Keychain salvage v3 draft — Style blocked |
| repoprompt-ce | #50, #51, #52 | T3 | Jules/Palette/Bolt — Style blocked |
| repoprompt-ce | #42–#46 | T3 | dependabot cluster — Style blocked |
