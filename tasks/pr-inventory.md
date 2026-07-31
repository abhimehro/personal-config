# PR Inventory — 2026-07-30 (Phase 2 salvage)

**Preflight:** PASS (7/7 repos) · `make cursor-cloud-hooks`  
**Mode:** salvage (Phase 2) · **never auto-merge** (S1)  
**Auth:** `GH_TOKEN` PAT as `abhimehro` (close/create OK — Lesson **0ew**)  
**Branch:** `cursor-agent/automated-pr-salvage-workflow-3cb9`  
**Input:** Phase 1 remainder via draft [#1832](https://github.com/abhimehro/personal-config/pull/1832) (`pr-review-2026-07-30.md`) + live re-fetch

## Live CONFLICTING queue at Phase 2 start

| Repo | PR | Author signal | Disposition |
|------|----|---------------|-------------|
| personal-config | [#1827](https://github.com/abhimehro/personal-config/pull/1827) | Sentinel | **CLOSED** superseded (#1828 pin) |
| personal-config | [#1821](https://github.com/abhimehro/personal-config/pull/1821) | Bolt/scratch | **CLOSED** no-op (scratch_triage) |
| personal-config | [#1820](https://github.com/abhimehro/personal-config/pull/1820) | Bolt + junk | **SALVAGE** → [#1836](https://github.com/abhimehro/personal-config/pull/1836) |
| personal-config | [#1819](https://github.com/abhimehro/personal-config/pull/1819) | Bolt | **CLOSED** prefer CLEAN [#1831](https://github.com/abhimehro/personal-config/pull/1831) |
| Seatek_Analysis | [#563](https://github.com/abhimehro/Seatek_Analysis/pull/563) | Jules | **DEFER** API redesign |
| Seatek_Analysis | [#558](https://github.com/abhimehro/Seatek_Analysis/pull/558) | Jules | **SALVAGE** → [#565](https://github.com/abhimehro/Seatek_Analysis/pull/565) |
| Seatek_Analysis | [#557](https://github.com/abhimehro/Seatek_Analysis/pull/557) | Jules | **SALVAGE** → #565 |
| Seatek_Analysis | [#554](https://github.com/abhimehro/Seatek_Analysis/pull/554) | Jules | **DEFER** warn_on_* rename |
| Seatek_Analysis | [#553](https://github.com/abhimehro/Seatek_Analysis/pull/553) | Jules | **SALVAGE** → #565 |
| Seatek_Analysis | [#552](https://github.com/abhimehro/Seatek_Analysis/pull/552) | security | **ESCALATE** |
| Seatek_Analysis | [#551](https://github.com/abhimehro/Seatek_Analysis/pull/551) | Jules | **SALVAGE** → #565 |
| series_correction… | [#329](https://github.com/abhimehro/series_correction_project_updated/pull/329) | Jules | **SALVAGE** → [#333](https://github.com/abhimehro/series_correction_project_updated/pull/333) |
| series_correction… | [#327](https://github.com/abhimehro/series_correction_project_updated/pull/327) | Jules | **DEFER** large extract |
| series_correction… | [#320](https://github.com/abhimehro/series_correction_project_updated/pull/320) | auth+junk | **CLOSED** prefer #315 |
| series_correction… | [#315](https://github.com/abhimehro/series_correction_project_updated/pull/315) | auth | **ESCALATE** |
| series_correction… | [#313](https://github.com/abhimehro/series_correction_project_updated/pull/313) | junk+setup | **SALVAGE** → [#332](https://github.com/abhimehro/series_correction_project_updated/pull/332) |
| repoprompt-ce | [#151](https://github.com/abhimehro/repoprompt-ce/pull/151) | Bolt | **CLOSED** identical to merged #153 |
| repoprompt-ce | [#150](https://github.com/abhimehro/repoprompt-ce/pull/150) | Bolt | **SALVAGE** → [#157](https://github.com/abhimehro/repoprompt-ce/pull/157) |
| repoprompt-ce | [#149](https://github.com/abhimehro/repoprompt-ce/pull/149) | Jules | **SALVAGE** → #157 |
| repoprompt-ce | [#146](https://github.com/abhimehro/repoprompt-ce/pull/146) | Bolt | **SALVAGE** → #157 |

## Empty / quiet

- ctrld-sync: only health draft #1081 (UNSTABLE) — not salvage target
- email-security-pipeline: CLEAN drafts #1390/#1388 — prior salvage #1383 MERGED
- Hydrograph…: no open PRs (#434 MERGED)

## Prior-day salvage status (verified)

| Old | Salvage | Status |
|-----|---------|--------|
| esp #1381 | [#1383](https://github.com/abhimehro/email-security-pipeline/pull/1383) | MERGED |
| hg #434 | — | MERGED (was escalate) |
| pc #1812 | — | MERGED (Phase 1 docs) |
