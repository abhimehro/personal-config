# PR Inventory — Phase 2 Salvage — 2026-08-07

**Trigger:** cron `0 17 * * *` Phase 2 salvage  
**Preflight:** PASS 7/7 (+ `make cursor-cloud-hooks`)  
**Auth:** `abhimehro` PAT (Lesson 0ew)  
**Source:** Phase 1 [#1937](https://github.com/abhimehro/personal-config/pull/1937) / `pr-review-2026-08-07.md` remainder + live CONFLICTING re-fetch  
**Open at scan:** 48 across 7 repos

## Live CONFLICTING (botish)

| Repo | PR | Title | Notes |
|------|----|-------|-------|
| personal-config | [#1902](https://github.com/abhimehro/personal-config/pull/1902) | Add edge case tests for write_text_files | Contaminated junk + valuable tests → **SALVAGED → #1938** (closed) |
| repoprompt-ce | [#211](https://github.com/abhimehro/repoprompt-ce/pull/211) | a11y labels notification buttons | XCTSkip contamination → **SALVAGED → #213** (closed) |
| email-security-pipeline | [#1421](https://github.com/abhimehro/email-security-pipeline/pull/1421) | Bolt aiohttp alert webhook | Large S6 refactor → **ESCALATE** (not auto-salvaged) |

## Phase 1 remainder (re-fetched)

| Repo | PR | mergeState | Disposition |
|------|-----|------------|-------------|
| personal-config | [#1907](https://github.com/abhimehro/personal-config/pull/1907) | CLEAN | ESCALATE CORS |
| Seatek_Analysis | [#620](https://github.com/abhimehro/Seatek_Analysis/pull/620) | CLEAN | ESCALATE Sentinel path-hijack |
| Hydrograph… | [#484](https://github.com/abhimehro/Hydrograph_Versus_Seatek_Sensors_Project/pull/484) | CLEAN | ESCALATE sanitize_filename |
| series… | [#365](https://github.com/abhimehro/series_correction_project_updated/pull/365) | CLEAN | ESCALATE auth timing |
| series… | [#364](https://github.com/abhimehro/series_correction_project_updated/pull/364) | UNSTABLE | ESCALATE PBKDF2 |
| series… | [#371](https://github.com/abhimehro/series_correction_project_updated/pull/371) | CLEAN | REQUEST_CHANGES / CodeScene already triggered |
| email-security-pipeline | [#1444](https://github.com/abhimehro/email-security-pipeline/pull/1444) | UNSTABLE | ESCALATE opencv 5.x + pytest |
| repoprompt-ce | [#210](https://github.com/abhimehro/repoprompt-ce/pull/210) | UNSTABLE | ESCALATE TOCTOU + CI fail |
| ctrld-sync | [#1136](https://github.com/abhimehro/ctrld-sync/pull/1136) | UNSTABLE | ESCALATE mypy 2.x |

## Prior salvage drafts still open (human merge)

| Repo | PR | Title |
|------|-----|-------|
| series… | [#369](https://github.com/abhimehro/series_correction_project_updated/pull/369) | outdir OSError tests |
| email-security-pipeline | [#1437](https://github.com/abhimehro/email-security-pipeline/pull/1437) | sanitize_error_message fast-path (draft) |
| repoprompt-ce | [#206](https://github.com/abhimehro/repoprompt-ce/pull/206) | indexBytes reuse (draft) |
| repoprompt-ce | [#207](https://github.com/abhimehro/repoprompt-ce/pull/207) | stderr byte-count logging (draft) |

## Per-repo open snapshot

| Repo | Open | Botish | CONFLICTING bot |
|------|-----:|-------:|----------------:|
| personal-config | 5 | 4 | 1 → 0 after salvage |
| ctrld-sync | 5 | 4 | 0 |
| email-security-pipeline | 3 | 3 | 1 (escalated) |
| Seatek_Analysis | 11 | 11 | 0 |
| Hydrograph… | 9 | 9 | 0 |
| series… | 4 | 4 | 0 |
| repoprompt-ce | 11 | 11 | 1 → 0 after salvage |
