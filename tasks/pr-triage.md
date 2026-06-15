# PR Triage — 2026-06-15

## Duplicate / superseded groups

### ctrld-sync #899 → superseded by #901
- **Overlap:** both unroll Content-Type `any()` check in `main.py` hot path.
- **Keep:** #901 (newer Jules Bolt; functional CI green except CodeScene).
- **Close:** #899 (salvage draft; ruff FAIL; helper extraction differs but same intent).

### series_correction #119 → superseded by #121
- **Overlap:** both vectorize `scripts/processor.py` outlier/MAD path.
- **Keep:** #121 (superset: jump-loop vectorization + MAD refactor).
- **Close:** #119.

### personal-config #1248 vs #1242 — NOT duplicate
- Different files: #1248 touches `morning-brief.py`; #1242 touches palette docs + infuse script + analytics dashboard.
- Both proceed independently.

## Escalations (trust boundary / failing required checks)

| Repo | PR | Reason |
| --- | ---: | --- |
| personal-config | 1249 | CI/INFRA: pins `codescene-oss/pr-refactoring-agent` in workflow — toolchain trust boundary |
| ctrld-sync | 901 | CodeScene code health FAIL on delta |
| Hydrograph_Versus_Seatek_Sensors_Project | 257 | CodeScene code health FAIL |
| series_correction_project_updated | 121 | CodeScene code health FAIL |

## Merge order (this session)

1. personal-config Phase 1 tail (oldest first): 1234 → 1235 → 1242 → 1243 → 1248 → 1251 → 1252
2. email-security-pipeline: 1111 → 1112 → 1114
3. Seatek_Analysis: 315
4. Hydrograph: 261
5. repoprompt-ce: 7 → 8 → 9

## Closes before merges

- ctrld-sync #899 (duplicate of #901)
- series_correction #119 (superseded by #121)
