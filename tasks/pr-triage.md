# PR Triage — 2026-07-19 (Phase 2 salvage)

## Disposition counts

| Disposition | Count |
|-------------|------:|
| SALVAGE (new draft) | 1 |
| CLOSE-SUPERSEDED | 2 (#1030/#1032) |
| CLOSE (session docs folded) | 1 (#1695) |
| ESCALATE (unchanged) | 5 |
| Autonomous merge | 0 |

## Salvage map

| Old | New draft | Tier |
|-----|-----------|------|
| ctrld-sync #1030 | [#1031](https://github.com/abhimehro/ctrld-sync/pull/1031) | T3 CLI UX / CodeScene |

## Escalations (human)

| Tier | PR | Why |
|------|-----|-----|
| T1 | [sc #233](https://github.com/abhimehro/series_correction_project_updated/pull/233) | Auth implementation |
| T2 | [pc #1670](https://github.com/abhimehro/personal-config/pull/1670) | Gemini/gitleaks + shellcheck delete vs #1679 |
| T2 | [hg #374](https://github.com/abhimehro/Hydrograph_Versus_Seatek_Sensors_Project/pull/374) | numpy major |
| T2 | [rpce #126](https://github.com/abhimehro/repoprompt-ce/pull/126) / [#127](https://github.com/abhimehro/repoprompt-ce/pull/127) | tip-release artifact majors |

## Overlap / supersede notes

- ctrld-sync #1030 Jules if/else raised CodeScene Complex Method 9→11; salvage extracts `_print_bold_header` (Lesson 0ec)
- ctrld-sync #1032 same Jules branch re-opened after #1030 close → closed superseded by #1031 (Lesson 0ed)
- Prior evening salvage drafts #1677/#1678/#1679 already MERGED before this run
- esp #1267 already MERGED (no longer in queue)
