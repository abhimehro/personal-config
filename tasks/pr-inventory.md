# PR Inventory — Phase 2 Salvage 2026-08-12

Phase 2 cron (17:00 UTC). Preflight PASS (+ `make cursor-cloud-hooks`).
Auth: `abhimehro` PAT (Lesson 0ew). Mode: **salvage only — 0 autonomous merges (S1)**.

Input: Phase 1 draft [#1977](https://github.com/abhimehro/personal-config/pull/1977)
(`pr-review-2026-08-12.md` remainder) + live CONFLICTING re-fetch.

## Live CONFLICTING automation queue (start)

| Repo | PR | Author / pattern | Title |
| ---- | -- | ---------------- | ----- |
| personal-config | 1977 | app/cursor docs | Phase 1 session report 2026-08-12 |
| ctrld-sync | 1150 | Palette / abhimehro | Grammatical Polish for Dry Run Errors |
| Hydrograph… | 504 | Sentinel / abhimehro | Log injection via filename sanitization |
| series… | 378 | Sentinel / abhimehro | User enumeration timing attack |
| repoprompt-ce | 231 | Bolt / abhimehro | Cache DateFormatter allocations |
| repoprompt-ce | 224 | salvage / abhimehro | REPLInputParser edge-case coverage |

## Open PR counts (end of Phase 2, approx)

| Repo | Open |
| ---- | ---: |
| personal-config | 4 |
| ctrld-sync | 3 |
| email-security-pipeline | 1 |
| Seatek_Analysis | 2 |
| Hydrograph… | 2 |
| series_correction… | 4 |
| repoprompt-ce | 9 |
| **Total** | **25** |

## Salvage drafts opened this run

| Repo | New PR | Salvages |
| ---- | ------ | -------- |
| Hydrograph… | [#507](https://github.com/abhimehro/Hydrograph_Versus_Seatek_Sensors_Project/pull/507) | #504 |
| ctrld-sync | [#1159](https://github.com/abhimehro/ctrld-sync/pull/1159) | #1150 |
| repoprompt-ce | [#237](https://github.com/abhimehro/repoprompt-ce/pull/237) | #224/#186 |

## Closed this run

| Repo | PR | Reason |
| ---- | -- | ------ |
| Hydrograph… | 504 | Superseded by #507 |
| ctrld-sync | 1150 | Superseded by #1159 (contamination stripped) |
| series… | 378 | No-op — `dummy_todos.py` absent on main |
| repoprompt-ce | 224 | Superseded by clean #237 |
| personal-config | 1977 | Superseded by this Phase 2 docs PR (0fk recovery) |

## Still escalated / deferred (human)

See `tasks/pr-triage.md` — CORS/TOCTOU/majors/CodeScene holds unchanged.
