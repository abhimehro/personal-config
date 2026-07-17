# PR Triage — 2026-07-17 (Phase 2 salvage)

## Disposition counts

| Disposition | Count |
|-------------|------:|
| SALVAGE (new draft) | 3 |
| CLOSE-SUPERSEDED / NO-OP | 3 |
| CLOSE (session docs folded) | 2 |
| ESCALATE (unchanged) | 5 |
| Autonomous merge | 0 |

## Salvage map

| Old | New draft | Tier |
|-----|-----------|------|
| pc #1663 | [#1677](https://github.com/abhimehro/personal-config/pull/1677) | T3 tests |
| pc #1668 | [#1678](https://github.com/abhimehro/personal-config/pull/1678) | T3 docs |
| pc #1669 | [#1679](https://github.com/abhimehro/personal-config/pull/1679) | T3 CI perf |

## Escalations (human)

| Tier | PR | Why |
|------|-----|-----|
| T1 | [sc #233](https://github.com/abhimehro/series_correction_project_updated/pull/233) | Auth implementation |
| T1 | [esp #1267](https://github.com/abhimehro/email-security-pipeline/pull/1267) | GitGuardian credential fixtures |
| T2 | [pc #1670](https://github.com/abhimehro/personal-config/pull/1670) | Gemini workflow consolidation |
| T2 | [hg #374](https://github.com/abhimehro/Hydrograph_Versus_Seatek_Sensors_Project/pull/374) | numpy major |
| T2 | [rpce #126](https://github.com/abhimehro/repoprompt-ce/pull/126) / [#127](https://github.com/abhimehro/repoprompt-ce/pull/127) | tip-release artifact majors |

## Overlap / supersede notes

- pc #1666 fully absorbed by `main` sequential exception test — closed
- pc #1663 clustered with #1666; salvaged allowlist tests only (Lesson 0dv)
- hg #381 re-inlined helpers already extracted by #378 — closed (Lesson 0dy)
