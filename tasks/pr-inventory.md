# PR Inventory — 2026-07-17 17:00 UTC (Phase 2 salvage)

**Mode:** Phase 2 salvage-only (S1 — no autonomous merges)  
**Preflight:** PASS 6/6 (+ repoprompt-ce)  
**Branch:** `cursor-agent/automated-pr-salvage-e7fd`  
**Input:** Phase 1 remainder from [#1676](https://github.com/abhimehro/personal-config/pull/1676) + live re-fetch

## Live open at Phase 2 start (12)

| Repo | PR | Mergeable | Disposition | Notes |
|------|----:|-----------|-------------|-------|
| personal-config | [1676](https://github.com/abhimehro/personal-config/pull/1676) | DIRTY | CLOSE→session | Phase 1 docs; folded into this PR |
| personal-config | [1670](https://github.com/abhimehro/personal-config/pull/1670) | DIRTY | ESCALATE | Gemini workflow trust boundary (unchanged) |
| personal-config | [1669](https://github.com/abhimehro/personal-config/pull/1669) | DIRTY | SALVAGE | → [#1679](https://github.com/abhimehro/personal-config/pull/1679) |
| personal-config | [1668](https://github.com/abhimehro/personal-config/pull/1668) | DIRTY | SALVAGE | → [#1678](https://github.com/abhimehro/personal-config/pull/1678) |
| personal-config | [1666](https://github.com/abhimehro/personal-config/pull/1666) | DIRTY | CLOSE-SUPERSEDED | Already on `main` |
| personal-config | [1665](https://github.com/abhimehro/personal-config/pull/1665) | DIRTY | CLOSE→session | 2026-07-16 report folded here |
| personal-config | [1663](https://github.com/abhimehro/personal-config/pull/1663) | DIRTY | SALVAGE | → [#1677](https://github.com/abhimehro/personal-config/pull/1677) allowlist-only |
| email-security-pipeline | [1267](https://github.com/abhimehro/email-security-pipeline/pull/1267) | CLEAN | ESCALATE | GitGuardian / credential fixtures |
| Hydrograph_Versus_Seatek_Sensors_Project | [381](https://github.com/abhimehro/Hydrograph_Versus_Seatek_Sensors_Project/pull/381) | DIRTY | CLOSE-SUPERSEDED | `#378` helpers already on main; CodeScene regression |
| Hydrograph_Versus_Seatek_Sensors_Project | [374](https://github.com/abhimehro/Hydrograph_Versus_Seatek_Sensors_Project/pull/374) | CLEAN | ESCALATE | numpy 2.x major |
| series_correction_project_updated | [233](https://github.com/abhimehro/series_correction_project_updated/pull/233) | CLEAN | ESCALATE | Auth logic |
| repoprompt-ce | [126](https://github.com/abhimehro/repoprompt-ce/pull/126) | CLEAN | ESCALATE | download-artifact major |
| repoprompt-ce | [127](https://github.com/abhimehro/repoprompt-ce/pull/127) | CLEAN | ESCALATE | upload-artifact major |

## Zero-open repos

- ctrld-sync
- Seatek_Analysis

## Counts

| Metric | Count |
|--------|------:|
| Investigated | 12 |
| Salvage drafts opened | 3 |
| Closed superseded / no-op | 3 (+ 2 session-doc PRs after fold) |
| Escalations left open | 5 |
| Autonomous merges | **0** |
