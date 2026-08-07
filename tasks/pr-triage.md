# PR Triage — Phase 2 Salvage — 2026-08-07

## Disposition counts (this Phase 2 run)

- **SALVAGE (draft opened):** 2
- **CLOSE-SUPERSEDED:** 2
- **ESCALATE (commented):** 9
- **REQUEST_CHANGES / hold:** 1 (#371 CodeScene already posted)
- **Autonomous merges:** 0 (S1)

## Salvage decisions

| Old | New | Keep | Strip |
|-----|-----|------|-------|
| pc #1902 | [#1938](https://github.com/abhimehro/personal-config/pull/1938) | `TestWriteTextFiles` | `commit_wrapper.py`, `my_submit.py`, `commit_msg.txt`, `tasks/todo.md` wipe |
| rpce #211 | [#213](https://github.com/abhimehro/repoprompt-ce/pull/213) | `.accessibilityLabel` + palette append | `XCTSkip` in 3 unrelated test files |

## Escalate (security / majors / S6)

- pc #1907 — CORS trust boundary
- Seatek #620 — Sentinel path-hijack cluster head
- Hydrograph #484 — sanitize_filename / log injection
- series #365 / #364 — auth timing + PBKDF2
- esp #1421 — CONFLICTING aiohttp webhook (S6; Lesson 0fh fire-and-forget risk)
- esp #1444 — opencv 5.x major + pytest red
- rpce #210 — TOCTOU + failing shard
- ctrld #1136 — mypy 2.x major

## Overlaps / notes

- Prior drafts #369 / #1437 / #206 / #207 remain for human merge (not re-salvaged)
- esp #1437 does **not** subsume #1421
- Palette a11y for Chat already on main via #203; notification-row labels were still missing → #213
