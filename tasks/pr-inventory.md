# PR Inventory — 2026-06-05

**Preflight:** PASS (6/6 repos)  
**Session:** Salvage cron `0 17 * * *`  
**Branch:** `cursor-agent/automated-pr-salvage-workflow-9f39`  
**Config:** `tasks/pr-review-agent.config.yaml`

## Scope summary (end of salvage)

| Repo | Open in-scope (EOD) | CONFLICTING / DIRTY |
| --- | ---: | ---: |
| personal-config | 4 | 0 (originals closed → draft salvages) |
| ctrld-sync | 0 | 0 |
| email-security-pipeline | 5 | 0 |
| Seatek_Analysis | 1 | 0 |
| Hydrograph_Versus_Seatek_Sensors_Project | 1 | 0 |
| series_correction_project_updated | 0 | 0 |

## Merged this session (CLEAN squash)

| Repo | PR | Category | Title |
| --- | ---: | --- | --- |
| personal-config | [#1169](https://github.com/abhimehro/personal-config/pull/1169) | PERFORMANCE | Bolt: optimize chained or/all() conditions |
| Seatek_Analysis | [#263](https://github.com/abhimehro/Seatek_Analysis/pull/263) | SECURITY | Sentinel: subprocess environment denylist (HIGH) |

## Closed superseded (conflicted or broken salvage)

| Repo | Old PR | Salvage draft | Notes |
| --- | ---: | ---: | --- |
| personal-config | [#1165](https://github.com/abhimehro/personal-config/pull/1165) | [#1172](https://github.com/abhimehro/personal-config/pull/1172) | Palette perf-report WCAG/HTML meta |
| email-security-pipeline | [#1030](https://github.com/abhimehro/email-security-pipeline/pull/1030) | [#1036](https://github.com/abhimehro/email-security-pipeline/pull/1036) | v3 dropped `_set_secure_permissions`; v4 rebuild |
| email-security-pipeline | [#1021](https://github.com/abhimehro/email-security-pipeline/pull/1021) | [#1037](https://github.com/abhimehro/email-security-pipeline/pull/1037) | CONFLICTING v2 → import-os v3 from main |

## Open tail (human review)

| Repo | PR | State | Disposition |
| --- | ---: | --- | --- |
| personal-config | [#1171](https://github.com/abhimehro/personal-config/pull/1171) | MERGEABLE UNSTABLE | MERGE when CI green (Palette ARIA) |
| personal-config | [#1172](https://github.com/abhimehro/personal-config/pull/1172) | draft, UNSTABLE | MERGE when CI green (salvage #1165) |
| personal-config | [#1154](https://github.com/abhimehro/personal-config/pull/1154) | draft, UNSTABLE | MERGE when CI green (run_merges v3) |
| personal-config | [#1170](https://github.com/abhimehro/personal-config/pull/1170) | draft | Session docs — merge after artifact land |
| email-security-pipeline | [#1008](https://github.com/abhimehro/email-security-pipeline/pull/1008) | draft T1 | MERGE first (Zip Slip); CodeScene advisory fail |
| email-security-pipeline | [#1023](https://github.com/abhimehro/email-security-pipeline/pull/1023) | ready, UNSTABLE | MERGE when CI green (NLP eval security) |
| email-security-pipeline | [#1036](https://github.com/abhimehro/email-security-pipeline/pull/1036) | draft | MERGE when CI green (threat metrics #972) |
| email-security-pipeline | [#1037](https://github.com/abhimehro/email-security-pipeline/pull/1037) | draft | MERGE when CI green (import os #996) |
| email-security-pipeline | [#1006](https://github.com/abhimehro/email-security-pipeline/pull/1006) | UNSTABLE | MERGE-AFTER-FIX (bandit) |
| Seatek_Analysis | [#261](https://github.com/abhimehro/Seatek_Analysis/pull/261) | draft, UNSTABLE | MERGE when CI green (scanner perf) |
| Hydrograph | [#227](https://github.com/abhimehro/Hydrograph_Versus_Seatek_Sensors_Project/pull/227) | draft, UNSTABLE | MERGE when CI green (Bolt perf); CodeScene advisory |

## Live inventory snapshot (gh)

See `scripts/get_prs.sh` output in session branch commit or regenerate:

```bash
./scripts/get_prs.sh --config tasks/pr-review-agent.config.yaml
```
