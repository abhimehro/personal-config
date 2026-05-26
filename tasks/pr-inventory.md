# PR Inventory — 2026-05-25 (cron `0 13 * * *`)

**Preflight:** PASS (`scripts/preflight-gh-pr-automation.sh --config tasks/pr-review-agent.config.yaml`, 6/6 repos)

**Mode:** `review-and-merge` | **Stale threshold:** 30 days | **Merge strategy:** squash

## Summary

| Repo | In-scope at start | In-scope open (end) | Session actions |
| --- | ---: | ---: | --- |
| abhimehro/personal-config | 10 | 2 | 7 merged, 2 closed, 1 auto-fix |
| abhimehro/email-security-pipeline | 11 | 9 | 2 merged |
| abhimehro/Seatek_Analysis | 8 | 5 | 1 merged |
| abhimehro/ctrld-sync | 1 | 1 | 0 (benchmark fail) |
| abhimehro/series_correction_project_updated | 2 | 2 | 0 (conflicts) |
| abhimehro/Hydrograph_Versus_Seatek_Sensors_Project | 0 | 0 | — |

## Full inventory (session start)

| Repo | PR | Author | Branch | Category | CI | Conflicts | Session end |
| --- | ---: | --- | --- | --- | --- | --- | --- |
| personal-config | [#1050](https://github.com/abhimehro/personal-config/pull/1050) | abhimehro | `cursor-agent/salvage-*-1036` | SECURITY | tests fail → fixed | — | **MERGED** |
| personal-config | [#1051](https://github.com/abhimehro/personal-config/pull/1051) | abhimehro | salvage #1048 | REFACTOR | CodeScene fail | — | **DEFER** |
| personal-config | [#1052](https://github.com/abhimehro/personal-config/pull/1052) | abhimehro | salvage #1039 | SECURITY | CodeScene fail | — | **DEFER** |
| personal-config | [#1053](https://github.com/abhimehro/personal-config/pull/1053) | app/cursor | salvage report | CI/INFRA | CLEAN | — | **MERGED** |
| personal-config | [#1054](https://github.com/abhimehro/personal-config/pull/1054) | abhimehro | Bolt perf | PERFORMANCE | CLEAN | — | **MERGED** |
| personal-config | [#1055](https://github.com/abhimehro/personal-config/pull/1055) | abhimehro | Bolt cleanup | REFACTOR | CLEAN | — | **MERGED** |
| personal-config | [#1057](https://github.com/abhimehro/personal-config/pull/1057) | abhimehro | scratch_triage perf | PERFORMANCE | CodeScene fail | — | **CLOSED** superseded #1063 |
| personal-config | [#1060](https://github.com/abhimehro/personal-config/pull/1060) | abhimehro | workflow consolidate | CI/INFRA | CLEAN | — | **MERGED** |
| personal-config | [#1062](https://github.com/abhimehro/personal-config/pull/1062) | abhimehro | parallel gh pr list | PERFORMANCE | CLEAN | DIRTY post-wave | **CLOSED** superseded #1063 |
| personal-config | [#1063](https://github.com/abhimehro/personal-config/pull/1063) | abhimehro | `jules-*` autofix #992 | CI/INFRA | CLEAN | — | **MERGED** |
| email-security-pipeline | [#925](https://github.com/abhimehro/email-security-pipeline/pull/925) | abhimehro | Bolt regex | PERFORMANCE | CLEAN | — | **MERGED** |
| email-security-pipeline | [#926](https://github.com/abhimehro/email-security-pipeline/pull/926) | abhimehro | Black format | CI/INFRA | CLEAN | — | **MERGED** |
| email-security-pipeline | [#905–908, #913, #917, #919, #921, #927](https://github.com/abhimehro/email-security-pipeline/pulls) | abhimehro | Bolt / Jules | mixed | varies | CONFLICTING / fail | **DEFER / ESCALATE** |
| Seatek_Analysis | [#222](https://github.com/abhimehro/Seatek_Analysis/pull/222) | abhimehro | Bolt path safety | SECURITY | CLEAN | — | **MERGED** |
| Seatek_Analysis | [#209–214](https://github.com/abhimehro/Seatek_Analysis/pulls) | abhimehro | Bolt perf/refactor | mixed | CLEAN | CONFLICTING | **DEFER** |
| ctrld-sync | [#846](https://github.com/abhimehro/ctrld-sync/pull/846) | abhimehro | Bolt dedup | PERFORMANCE | benchmark **fail** | CONFLICTING | **DEFER** |
| series_correction | [#66](https://github.com/abhimehro/series_correction_project_updated/pull/66), [#68](https://github.com/abhimehro/series_correction_project_updated/pull/68) | abhimehro | Bolt | REFACTOR | CLEAN | CONFLICTING | **DEFER** |

## Open tail (end of session)

| Repo | PR | Reason |
| --- | ---: | --- |
| personal-config | #1051 | CodeScene required check failing |
| personal-config | #1052 | CodeScene failing; credential docs — human review recommended |
| email-security-pipeline | #919 | **ESCALATE** — TOCTOU / permission hardening in security-classified repo |
| email-security-pipeline | #905–908, #913, #917, #921, #927 | CONFLICTING after merge wave; rebase batch |
| Seatek_Analysis | #209–214 | CONFLICTING; CI green |
| ctrld-sync | #846 | Required **benchmark** check failing |
| series_correction | #66, #68 | CONFLICTING; CI green |
