# PR Inventory — 2026-06-22

**Preflight:** PASS (6/6 configured repos; repoprompt-ce checked ad hoc)\
**Phase 1:** cron `0 13 * * *` — review-and-merge (`cursor-agent/automated-pr-workflow-7912`)\
**Phase 2:** cron `0 17 * * *` — salvage-and-cleanup (`cursor-agent/pr-salvage-and-cleanup-a9e8`)\
**Config:** `tasks/pr-review-agent.config.yaml`

## Scope summary

| Repo | Open at start | Merged (Phase 1) | Closed dup/stale | Salvage actions | Deferred EOD | Open EOD |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| personal-config | 0 | 5 | 0 | 0 | 0 | 1 |
| ctrld-sync | 0 | 2 | 1 | 0 | 0 | 0 |
| email-security-pipeline | 0 | 1 | 0 | 0 | 0 | 0 |
| Seatek_Analysis | 0 | 2 | 0 | 0 | 0 | 0 |
| Hydrograph_Versus_Seatek_Sensors_Project | 0 | 0 | 0 | 0 | 0 | 0 |
| series_correction_project_updated | 6 | 5 | 1 | 0 | 1 | 1 |
| repoprompt-ce | 5 | 1 | 2 | 2 | 3 | 4 |

**Phase 1 totals:** 24 inventoried · 15 merges · 4 closes · 1 auto-fix · 5 deferred\
**Phase 2 totals:** 7 repos · 1 salvage v3 · 1 close-superseded · 2 update-branch · 0 autonomous merges

## Phase 1 inventory at session start (salvage tail from 2026-06-21)

| Repo | PR | Prior status | Phase 1 outcome |
| --- | ---: | --- | --- |
| personal-config | #1311 | T0 infra-fix draft | **MERGED** |
| personal-config | #1310 | T1 Sentinel CWE-78 | **MERGED** |
| ctrld-sync | #932 | CodeScene defer | **MERGED** |
| email-security-pipeline | #1138 | CLEAN merge candidate | **MERGED** |
| repoprompt-ce | #29 | T0 infra-fix draft | **MERGED** |
| series_correction | #135 | CodeScene defer | **CLOSED** → superseded by #142 |
| repoprompt-ce | #27 | Bolt perf DIRTY | **CLOSED** → superseded by #39 |
| repoprompt-ce | #28 | T1 Keychain v2 DIRTY | **OPEN** at Phase 1 EOD |
| repoprompt-ce | #24, #25 | T3 salvage UNSTABLE | **OPEN** at Phase 1 EOD |

## Phase 2 salvage queue at start

| Repo | PR | Merge | CI | Disposition |
| --- | ---: | --- | --- | --- |
| repoprompt-ce | #28 | CONFLICTING | Style + dependency-review | **CLOSE → v3 salvage #41** |
| repoprompt-ce | #24 | MERGEABLE | Style + dependency-review | **update-branch** → snyk only |
| repoprompt-ce | #25 | MERGEABLE | Style + dependency-review | **update-branch** → snyk only |
| repoprompt-ce | #39 | MERGEABLE | snyk + build | **ESCALATE** (trust boundary) |
| series_correction | #142 | MERGEABLE | CodeScene fail | **DEFER** (cs-agent posted) |

**Conflict queue:** 1 DIRTY (#28) — cleared via v3 re-salvage

## Open at Phase 2 EOD

| Repo | PR | Tier | Reason |
| --- | ---: | --- | --- |
| personal-config | [#1324](https://github.com/abhimehro/personal-config/pull/1324) | — | Draft Phase 1 session report |
| repoprompt-ce | [#41](https://github.com/abhimehro/repoprompt-ce/pull/41) | T1 | Keychain salvage v3 draft (from #28) |
| repoprompt-ce | [#39](https://github.com/abhimehro/repoprompt-ce/pull/39) | T2 | ESCALATE — bot disabled security CI + scope creep |
| repoprompt-ce | [#24](https://github.com/abhimehro/repoprompt-ce/pull/24) | T3 | Linux tests salvage; snyk only fail |
| repoprompt-ce | [#25](https://github.com/abhimehro/repoprompt-ce/pull/25) | T3 | a11y salvage; snyk only fail |
| series_correction | [#142](https://github.com/abhimehro/series_correction_project_updated/pull/142) | T3 | Bolt vectorize; CodeScene fail |
