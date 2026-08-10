# PR Inventory — 2026-08-10

Phase 2 salvage cron (`0 17 * * *`). Preflight **PASS** (+ `make cursor-cloud-hooks`).
Auth: `abhimehro` PAT (Lesson 0ew). **Autonomous merges: 0 (S1).**

Input: Phase 1 [#1953](https://github.com/abhimehro/personal-config/pull/1953) /
`pr-review-2026-08-09.md` remainder + live re-fetch of CONFLICTING/DIRTY bot PRs.

## Live CONFLICTING / DIRTY (start → disposition)

| Repo | PR | Shape | Disposition |
| ---- | -- | ----- | ----------- |
| email-security-pipeline | [#1421](https://github.com/abhimehro/email-security-pipeline/pull/1421) | Bolt aiohttp + contamination | ESCALATE (0fh / S6) |
| series_correction… | [#364](https://github.com/abhimehro/series_correction_project_updated/pull/364) | Sentinel PBKDF2 `dummy_todos` | ESCALATE (auth boundary / 0ef) |
| repoprompt-ce | [#196](https://github.com/abhimehro/repoprompt-ce/pull/196) | TOCTOU + Changelog/journal churn | ESCALATE (cluster) |

## Salvage / close actions this run

| Repo | Old PR | Action | New / note |
| ---- | -----: | ------ | ---------- |
| email-security-pipeline | 1459 | CLOSE no-op | Jules Daily QA zero-diff (0/0) |
| repoprompt-ce | 184 | SALVAGE + CLOSE | [#227](https://github.com/abhimehro/repoprompt-ce/pull/227) MCPCommandParserTests + portable `stat` |

## Open salvage drafts awaiting human (queue)

| Repo | PR | Note |
| ---- | -- | ---- |
| series_correction… | [#379](https://github.com/abhimehro/series_correction_project_updated/pull/379) | Aug 9 — lazy `log.exception` (CLEAN) |
| series_correction… | [#375](https://github.com/abhimehro/series_correction_project_updated/pull/375) | Aug 8 — OSError test; CodeScene-only fail |
| repoprompt-ce | [#227](https://github.com/abhimehro/repoprompt-ce/pull/227) | **NEW** — MCPCommandParser tests (salvages #184) |
| repoprompt-ce | [#224](https://github.com/abhimehro/repoprompt-ce/pull/224) | Aug 9 — REPLInputParser edges (CLEAN) |
| repoprompt-ce | [#218](https://github.com/abhimehro/repoprompt-ce/pull/218) | Aug 8 — ToolGroupsCatalog tests |

## Open auto inventory snapshot (EOD approx)

| Repo | Open | Notes |
| ---- | ---: | ----- |
| personal-config | 6 | #1953/#1954 docs + #1907 CORS + Palette/Bolt |
| ctrld-sync | 6 | #1135/#1136 deps; #1147 Sentinel PRNG; Bolt/Palette |
| email-security-pipeline | 4 | #1421 DIRTY; #1444 opencv major; Bolt/Palette |
| Seatek_Analysis | 18 | Sentinel path-hijack / timeout cluster |
| Hydrograph… | 16 | sanitize_filename Sentinel cluster |
| series_correction… | 6 | #364 DIRTY; #365/#378 auth; #379/#375 drafts |
| repoprompt-ce | ~9 | TOCTOU cluster; #227/#224/#218 drafts; Palette |

## Security / major holds (never Phase-2 merge)

- CORS: pc [#1907](https://github.com/abhimehro/personal-config/pull/1907)
- Auth timing / PBKDF2: series [#365](https://github.com/abhimehro/series_correction_project_updated/pull/365), [#364](https://github.com/abhimehro/series_correction_project_updated/pull/364), [#378](https://github.com/abhimehro/series_correction_project_updated/pull/378)
- TOCTOU: rpce [#217](https://github.com/abhimehro/repoprompt-ce/pull/217)/[#223](https://github.com/abhimehro/repoprompt-ce/pull/223)/[#214](https://github.com/abhimehro/repoprompt-ce/pull/214)/[#210](https://github.com/abhimehro/repoprompt-ce/pull/210)/[#201](https://github.com/abhimehro/repoprompt-ce/pull/201)/[#196](https://github.com/abhimehro/repoprompt-ce/pull/196)
- Majors: esp [#1444](https://github.com/abhimehro/email-security-pipeline/pull/1444) opencv 5.x; ctrld [#1136](https://github.com/abhimehro/ctrld-sync/pull/1136) mypy 2.x
- Sentinel clusters: Seatek path-hijack (~#640…#573); Hydrograph sanitize (~#500…#459)
