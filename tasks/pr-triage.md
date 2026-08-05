# PR Triage — 2026-08-05

## Duplicate / overlap groups

| Group | PRs | Keep | Close |
| ----- | --- | ---- | ----- |
| Seatek Bolt top-N | #608, #606 | #608 (merged) | #606 closed |
| pc Palette empty-state | #1918, #1915 | #1918 (merged) | #1915 closed |
| Hydrograph sanitize_filename Sentinels | #473, #468, #466, #459 | Prefer #466 (human) | leave open until human confirms |
| Seatek subprocess Sentinels | #607, #605, #590, #585, #580 (+#573 distinct) | Prefer #605 | leave open |
| series pandas import | #363, #361 | #363 (merged) | #361 closed |
| Seatek "🧪 test" prod-rename cluster | #601, #599, #598, #596, #595 | none | REQUEST_CHANGES all |

## Conflict cascade notes

- After #1918, #1913 flipped DIRTY on `.jules/palette.md` — autofixed (kept both journal entries) then merged.
- Hydrograph #461 (lock) merged after #470 (requirements-only); #471 (pandas major + lock) held escalated — no lock cascade this pass.

## Stale (>30d)

None in this inventory.

## Security-first holds

All Sentinel / CORS / TOCTOU / Keychain / PBKDF2 / path-hijack PRs → ESCALATE regardless of green CI.
