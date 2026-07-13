# PR Inventory — 2026-07-13

**Trigger:** Cron Phase 1 `0 13 * * *`  
**Agent branch:** `cursor-agent/automated-pr-workflow-bbeb`  
**Mode:** review-and-merge  
**Preflight:** PASS 6/6 configured repos (+ repoprompt-ce scanned ad hoc)

## Summary

| Metric | Count |
|--------|------:|
| Repos scanned | 7 |
| In-scope open at start | 18 |
| In-scope open at end | 5 |

## Full inventory (start of session)

| Repo | PR | Author | Category | CI | Conflicts | Age (days) | Automation hints | Status (EOD) |
|------|-----|--------|----------|-----|-----------|------------|------------------|--------------|
| personal-config | [#1600](https://github.com/abhimehro/personal-config/pull/1600) | abhimehro | PERFORMANCE | GREEN | CLEAN | 0 | bolt | **MERGED** |
| personal-config | [#1598](https://github.com/abhimehro/personal-config/pull/1598) | abhimehro | UI | GREEN | CLEAN | 1 | palette | **MERGED** |
| personal-config | [#1597](https://github.com/abhimehro/personal-config/pull/1597) | abhimehro | CI/INFRA | GREEN | CLEAN | 1 | jules QA | **CLOSED** (no-op) |
| personal-config | [#1594](https://github.com/abhimehro/personal-config/pull/1594) | app/cursor | CI/INFRA | GREEN | CLEAN | 1 | cursor-agent draft | **CLOSED** (superseded) |
| personal-config | [#1593](https://github.com/abhimehro/personal-config/pull/1593) | abhimehro | SECURITY | GREEN | CLEAN | 1 | sentinel | **ESCALATE** |
| personal-config | [#1592](https://github.com/abhimehro/personal-config/pull/1592) | app/cursor | CI/INFRA | GREEN | CLEAN | 1 | cursor-agent draft | **CLOSED** (superseded) |
| ctrld-sync | [#1005](https://github.com/abhimehro/ctrld-sync/pull/1005) | abhimehro | SECURITY | GREEN | CLEAN | 1 | sentinel/jules | **MERGED** |
| ctrld-sync | [#1004](https://github.com/abhimehro/ctrld-sync/pull/1004) | abhimehro | UI | GREEN | CLEAN | 1 | palette/jules | **MERGED** |
| ctrld-sync | [#990](https://github.com/abhimehro/ctrld-sync/pull/990) | abhimehro | SECURITY | FAIL (benchmark) | UNSTABLE | 4 | SSRF allowlist | **ESCALATE** |
| email-security-pipeline | — | — | — | — | — | — | — | zero open |
| Seatek_Analysis | — | — | — | — | — | — | — | zero open |
| Hydrograph_Versus_Seatek_Sensors_Project | [#352](https://github.com/abhimehro/Hydrograph_Versus_Seatek_Sensors_Project/pull/352) | abhimehro | PERFORMANCE | FAIL (CodeScene) | UNSTABLE | 1 | bolt | **CLOSED** (duplicate) |
| Hydrograph_Versus_Seatek_Sensors_Project | [#351](https://github.com/abhimehro/Hydrograph_Versus_Seatek_Sensors_Project/pull/351) | abhimehro | PERFORMANCE | FAIL (CodeScene) | UNSTABLE | 1 | bolt/jules | **CLOSED** (duplicate) |
| Hydrograph_Versus_Seatek_Sensors_Project | [#349](https://github.com/abhimehro/Hydrograph_Versus_Seatek_Sensors_Project/pull/349) | abhimehro | CI/INFRA | GREEN | CLEAN | 1 | jules QA | **CLOSED** (no-op) |
| Hydrograph_Versus_Seatek_Sensors_Project | [#344](https://github.com/abhimehro/Hydrograph_Versus_Seatek_Sensors_Project/pull/344) | abhimehro | PERFORMANCE | FAIL (CodeScene) | UNSTABLE | 4 | bolt | **DEFER** |
| series_correction_project_updated | [#222](https://github.com/abhimehro/series_correction_project_updated/pull/222) | abhimehro | PERFORMANCE | GREEN | CLEAN | 0 | bolt | **MERGED** |
| series_correction_project_updated | [#221](https://github.com/abhimehro/series_correction_project_updated/pull/221) | abhimehro | CI/INFRA | GREEN | CLEAN | 1 | jules QA | **CLOSED** (no-op) |
| series_correction_project_updated | [#218](https://github.com/abhimehro/series_correction_project_updated/pull/218) | abhimehro | PERFORMANCE | GREEN | CLEAN | 4 | cursor-agent salvage | **CLOSED** (superseded by #222) |
| series_correction_project_updated | [#210](https://github.com/abhimehro/series_correction_project_updated/pull/210) | abhimehro | SECURITY | GREEN | CLEAN | 4 | cursor-agent salvage | **ESCALATE** |
| repoprompt-ce | [#112](https://github.com/abhimehro/repoprompt-ce/pull/112) | abhimehro | SECURITY | GREEN | CLEAN | 4 | sentinel/jules | **ESCALATE** |

## Remaining open (EOD)

| Repo | PR | Disposition |
|------|-----|-------------|
| personal-config | [#1593](https://github.com/abhimehro/personal-config/pull/1593) | ESCALATE — command injection trust boundary |
| ctrld-sync | [#990](https://github.com/abhimehro/ctrld-sync/pull/990) | ESCALATE — SSRF allowlist + benchmark fail |
| Hydrograph_Versus_Seatek_Sensors_Project | [#344](https://github.com/abhimehro/Hydrograph_Versus_Seatek_Sensors_Project/pull/344) | DEFER — CodeScene FAIL; cs-agent remediation |
| series_correction_project_updated | [#210](https://github.com/abhimehro/series_correction_project_updated/pull/210) | ESCALATE — CLI exception sanitization |
| repoprompt-ce | [#112](https://github.com/abhimehro/repoprompt-ce/pull/112) | ESCALATE — URLSession ephemeral hardening |
