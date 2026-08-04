# PR Triage — 2026-08-04

## Disposition counts

- **MERGE**: 54
- **CLOSE**: 5
- **ESCALATE**: 10
- **REQUEST_CHANGES**: 19
- **DEFER**: 0

## Overlaps / twins

- esp #1420 (red) vs #1421 (green aiohttp) → close #1420; RC #1421
- ctrld #1115 vs #1111 Palette hint → prefer #1111; close #1115 (.Jules case collision)
- Hydrograph #460/#461 share poetry.lock → merge one-at-a-time (0fb)
- Seatek repository_automation_*.py cascade → RC mislabeled prod refactors
- personal-config performance_optimizer.sh: #1886/#1890/#1893 → cascade-aware

## Journal wipe / hijack closes

- #1897, #1418 — Lesson 0fc
- #1898 — LICENSE/README replaced with Gitleaks upstream content

## Escalate (security / trust boundary)

- [Hydrograph_Versus_Seatek_Sensors_Project#466](https://github.com/abhimehro/Hydrograph_Versus_Seatek_Sensors_Project/pull/466) — Security/Sentinel trust-boundary
- [Hydrograph_Versus_Seatek_Sensors_Project#459](https://github.com/abhimehro/Hydrograph_Versus_Seatek_Sensors_Project/pull/459) — Security/Sentinel trust-boundary
- [Seatek_Analysis#590](https://github.com/abhimehro/Seatek_Analysis/pull/590) — Security/Sentinel trust-boundary
- [Seatek_Analysis#585](https://github.com/abhimehro/Seatek_Analysis/pull/585) — Security/Sentinel trust-boundary
- [Seatek_Analysis#580](https://github.com/abhimehro/Seatek_Analysis/pull/580) — Security/Sentinel trust-boundary
- [Seatek_Analysis#573](https://github.com/abhimehro/Seatek_Analysis/pull/573) — Security/Sentinel trust-boundary
- [personal-config#1907](https://github.com/abhimehro/personal-config/pull/1907) — Security/Sentinel trust-boundary
- [repoprompt-ce#193](https://github.com/abhimehro/repoprompt-ce/pull/193) — Sentinel stderr secret exposure
- [repoprompt-ce#192](https://github.com/abhimehro/repoprompt-ce/pull/192) — Sentinel Keychain auth bypass
- [series_correction_project_updated#357](https://github.com/abhimehro/series_correction_project_updated/pull/357) — CWE-209 exception leakage

## Phase 2 triage (2026-08-04 17:00 UTC)

| Disposition | Count | Notes |
|-------------|------:|-------|
| SALVAGE draft | 4 | #1913, #603, #360, #195 |
| CLOSE-SUPERSEDED | 2 | series#357, rpce#188 |
| CLOSE harmful | 1 | seatek#600 |
| ESCALATE comments | 9 | Sentinels (pc/seatek/hg/rpce) |
| REQUEST_CHANGES | 3 | esp#1421, seatek#601/#595 |
| AUTO-RESOLVED note | 1 | hg#461 |
| Autonomous merges | 0 | S1 |

Priority for human: merge salvage drafts (CodeScene pending on series#360), then T1 Sentinels.
