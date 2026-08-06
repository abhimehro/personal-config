# PR Triage — 2026-08-06 Phase 2 Salvage

Decision tree per `docs/automated-pr-salvage-agent.md` (S1–S6).
Input: Phase 1 `pr-review-2026-08-06.md` remainder + live CONFLICTING re-fetch.
Autonomous merges: **0**.

## Disposition summary

| Disposition | Count | PRs |
| ----------- | ----: | --- |
| SALVAGE (draft) | 4 | series [#369](https://github.com/abhimehro/series_correction_project_updated/pull/369); esp [#1437](https://github.com/abhimehro/email-security-pipeline/pull/1437); rpce [#206](https://github.com/abhimehro/repoprompt-ce/pull/206), [#207](https://github.com/abhimehro/repoprompt-ce/pull/207) |
| CLOSE-SUPERSEDED / no-op | 9 | series#360; esp#1409; rpce#195/#193; pc#1904; Seatek#595/#598/#599/#601 |
| ESCALATE (human T1) | ~20 | pc#1907; Seatek Sentinel cluster; Hydrograph sanitize cluster; esp#1421/#1431/#1432; series#364/#365; rpce#196/#201 |
| REQUEST_CHANGES / HOLD | 3 | pc#1924/#1902; rpce#203 CI a11y |
| Empty CONFLICTING | 2 repos | ctrld-sync; Hydrograph (no DIRTY after Phase 1) |

## Deep-dive notes

### series#360 → #369
Prior salvage draft contaminated by Code Health reshuffle of whole
`test_batch_correction.py`. Re-salvaged **only**
`test_ensure_output_directory_oserror` (Lesson **0fj**). pytest passed locally.

### esp#1409 → #1437
Kept `sanitize_error_message` http/www fast-path. Rejected `media_analyzer`
CodeScene extract (0fc). Omitted PR tip's bare `/` from fast-path skip set.

### rpce#195 → #206
Re-applied `optionalIndexBytes` reuse; journal append-only (0y).

### rpce#193 → #207
Mega-diff (+894/−3299) → salvaged **CLIEnvironmentCache** stderr→byte-count only.

### pc#1904 / Seatek#595–601
Closed: scope collapse / 0ff production renames under test titles.

## Security gates
- No auth/payment/schema changes implemented.
- ESP S6: salvage draft only.
- Skip `request_reviewers` when author is abhimehro (0ew).
