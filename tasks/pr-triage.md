# PR Triage — 2026-06-19

**Mode:** salvage-and-cleanup (Phase 2)\
**Preflight:** PASS\
**Input:** Live GitHub state + deferred tail from `tasks/pr-review-2026-06-16.md`

## Triage matrix (Phase 2)

| Disposition | Count | Action |
| --- | ---: | --- |
| SALVAGE (new draft PR) | 2 | pc #1279 → #1287; pc #1281 → #1288 |
| CLOSE-SUPERSEDED | 3 | pc #1279, #1281, #1280 |
| DEFER (Phase 1 / human merge) | 2 | pc #1284; sc #121 |
| ESCALATE T0 | 0 | — |

## Infra detection

**No whole-repo infra breakage detected.** All configured repos readable; five repos have zero open PRs.

## Duplicate & overlap analysis

| Group | Keeper | Closed | Rationale |
| --- | --- | --- | --- |
| pc Sentinel AppleScript fix | **#1287** (salvage) | #1279 | DIRTY after session-file merges; one-line `--` fix only |
| pc Palette podcast a11y | **#1288** (salvage) | #1281 | DIRTY; CodeScene refactors omitted, a11y one-liner kept |
| pc session docs | **salvage branch** | #1280 | DIRTY draft session report superseded by 2026-06-19 run |
| sc vectorize perf | **#121** | — | CodeScene tail; cs-agent already invoked |

## Per-PR notes

### personal-config #1287 — SALVAGE (draft, T1)

Rebuilt from #1279 with only `configs/.config/mole/lib/core/sudo.sh` on current `main`. Adds `--` before `MOLE_SUDO_PROMPT` in osascript ASKPASS to block CWE-74 injection. Local `bash -n` passed.

### personal-config #1288 — SALVAGE (draft, T3)

Rebuilt from #1281 with only the podcast error-path `html_section()` change in `scripts/morning-brief/morning-brief.py`. Intentionally omitted CodeScene-driven `_parse_linear_focus_node` inlining from the original PR.

### personal-config #1284 — DEFER (Phase 1)

`chore(actions): consolidate workflow automation` — CLEAN, all checks green including CodeScene. Trust-boundary change (`.github/workflows/*`); human merge recommended.

### series_correction #121 — DEFER

MERGEABLE but CodeScene failing. `/cs-agent skill:fix-code-health-degradations` already posted 2026-06-15; no new salvage branch opened.
