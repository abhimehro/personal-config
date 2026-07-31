# PR Triage — 2026-07-30 Phase 2

## Decision rules applied

- S1: never auto-merge salvage drafts
- S2: skip journals (`.jules/*`)
- S4: adapt tests to main APIs (truncate assertion; no blind checkout)
- 0es: prefer CLEAN twin (#1831 over #1819; #153 over #151)
- 0et: surgical residuals when changed-in-both
- Auth/CORS/injection → ESCALATE only (no salvage of auth)

## Counts

| Disposition | Count |
|-------------|------:|
| CLOSE-SUPERSEDED / no-op | 8 |
| SALVAGE drafts opened | 5 |
| ESCALATE (MCP) | 3 |
| REQUEST_CHANGES | 1 (#144) |
| DEFER | 3 (#554/#563/#327) |
| Autonomous merges | **0** |

## Salvage drafts awaiting human

1. [pc #1836](https://github.com/abhimehro/personal-config/pull/1836) — GraphQL batch `run_merges` (from #1820, no trunk junk)
2. [seatek #565](https://github.com/abhimehro/Seatek_Analysis/pull/565) — automation unit tests + `flattened_updates` fix
3. [series #332](https://github.com/abhimehro/series_correction_project_updated/pull/332) — setup.py `__future__` cleanup
4. [series #333](https://github.com/abhimehro/series_correction_project_updated/pull/333) — `parse_year_pair` tests
5. [rpce #157](https://github.com/abhimehro/repoprompt-ce/pull/157) — Swift micro-opts (#146/#149/#150)

## Human T1 escalations

1. [pc #1822](https://github.com/abhimehro/personal-config/pull/1822) — CORS fail-closed
2. [seatek #552](https://github.com/abhimehro/Seatek_Analysis/pull/552) — `run_shell_command` list-only
3. [series #315](https://github.com/abhimehro/series_correction_project_updated/pull/315) — `authenticate()` repair

## Prefer Phase 1 CLEAN twins (not salvaged)

- [pc #1831](https://github.com/abhimehro/personal-config/pull/1831) — defaultdict (covers #1819)
