# PR Triage — 2026-08-08

## Overlap / duplicates

| Group | Keep | Close | Reason |
| ----- | ---- | ----- | ------ |
| pc TruffleHog renames | #1935 | #1941 | Same 4 test files; different rename strings; pick older green |
| Seatek sprintf Bolt | #628 | #623 | Same R hunk; #628 fewer noise comments |
| rpce DateFormatter Bolt | #212 | #216 | #212 green; #216 failing shard 4 |
| Seatek zero-diff | — | #617, #626 | `changedFiles=0` |
| ctrld uv.lock Dependabot | #1134 first | do not close #1133/#1135 | Distinct bumps; rebase after lock merge (0fb) |

## Security clusters (ESCALATE — Phase 2)

- personal-config#1907 CORS allow-all
- Seatek_Analysis#620 (+ #573/#580/#585/#590/#605/#607/#610/#612/#624/#627) path-hijack / subprocess
- Hydrograph#484 (+ #459/#466/#468/#473/#475/#478/#483/#486/#488) sanitize_filename
- series#364 PBKDF2, #365 auth timing
- rpce#210 (+ #196/#201/#214) TOCTOU
- esp#1437 sanitize_error_message fast-path **leaks** bare-path webhook secrets (adversarial consensus)
- ctrld#1136 mypy 2.x major; esp#1444 opencv 5.x major

## CodeScene / RC

- esp#1447 Palette UX — CodeScene red → post `/cs-agent skill:fix-code-health-degradations`
- series#372, #374 — CodeScene red → same trigger
- rpce#184 — failing Build shard 1

## Adversarial synthesis (opus-4.8 + gpt-5.5)

| Finding | Models | Verdict |
| ------- | ------ | ------- |
| esp#1437 sanitizer bypass | both critical | **Act on** — ESCALATE, do not merge |
| ctrld#1133/#1135 not twins of #1134 | opus | **Act on** — defer/rebase, don't close |
| pc#1943 `set -e` cat race | gpt warning | **Consider** — merge; local dashboard; pre-existing soft-fail pattern |
| pc#1945 id() cache footgun | opus nit | **Noted** — constants-only callers |
| Remaining MERGE set | both | **Dismiss** — safe |

---

## Phase 2 addendum (2026-08-08)

# PR Triage — Phase 2 Salvage 2026-08-08

## Decision summary

| Bucket | Action | PRs |
|--------|--------|-----|
| Salvage drafts (new) | Open `--draft` on fresh main | series [#375](https://github.com/abhimehro/series_correction_project_updated/pull/375); rpce [#218](https://github.com/abhimehro/repoprompt-ce/pull/218) |
| Close superseded / no-op | Close + comment | #369, #194, #187, #374, #1939 |
| Close rejected (security) | Close + comment | esp #1437 (0fl) |
| Escalate human T1 | Comment only | #1907, #620, #484, #365, #364, #1421, #1444, #1136, #210, #196 |
| Hold REQUEST_CHANGES | CodeScene already posted | series #372; esp #1447 |
| Not merged | **0 autonomous merges (S1)** | — |

## Security gates applied

- **S1** No autonomous merges
- **S6** ESP #1421 held; #1437 closed rather than re-salvaged
- **0fj** Unique-assertion / unique-file only for #369/#194
- **0fk** One competing `tasks/*` docs writer this pass (this branch); closed #1939 after recovery
- **0fl** Sanitizer fast-path rejected
- **0ew** Skip `request_reviewers` when author is `abhimehro`

## Human priority order

1. Merge salvage drafts #375 → #218 (after macOS ToolGroupsTests)
2. T1 security: #1907 CORS; Seatek #620; Hydrograph #484; series #365/#364; rpce #217 (prefer over #210/#196); esp #1421
3. Majors: ctrld #1136; esp #1444
4. Merge Phase 1 docs [#1946](https://github.com/abhimehro/personal-config/pull/1946) then this Phase 2 docs PR (0fk)
