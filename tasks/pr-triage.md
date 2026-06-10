# PR Triage — 2026-06-08

**Preflight:** PASS (6/6)  
**Disposition key:** MERGE · CLOSE-ZERO-DIFF · DEFER · ESCALATE
**Session logs:** review writes to `tasks/review-session-reports.md`; salvage writes to `tasks/salvage-session-reports.md`.

## Duplicate & overlap analysis

| Group | Keeper | Action on others | Rationale |
| --- | --- | --- | --- |
| Jules lint fix (ESP) | **#1054** | Close #1053 | Identical `tests/test_ui_palette.py` diff; #1054 newer (Lesson 0ds) |
| Jules QA zero-diff (personal-config) | **none** | Close #1189 | `changedFiles == 0` (Lesson 0cf) |
| Salvage session docs (personal-config) | **This session branch** | Close #1185 | Supersedes 2026-06-07 evening salvage draft |
| Perf salvage drafts (sa/hg) | **None** | Defer #261, #227 | Fifth consecutive session; CodeScene sole failure |
| Sentinel stack trace (scp) | **#102** | Phase 1 merge | T1 security; all gates green — salvage policy defers merge to Phase 1 / human |

No semantic duplicates among remaining open PRs.
| ESP spam/UI cluster | **#1054 → #1056 → #1058 → #1060** | Merge all in order | Shared files (`spam_analyzer.py`, `setup_wizard.py`, `test_ui_palette.py`) but distinct intents: lint, Palette colorize, URL Counter perf, Jules QA formatting/timeouts |
| Sentinel security (hg/sc) | **#237, #102** | (none) | Independent repos; both defense-in-depth hardening |
| Bolt perf (pc/sa) | **#1195, #270** | (none) | Independent files (`scratch_inventory.py` vs `code_health_scanner.py`) |
| Salvage perf drafts (sa/hg) | **None** | Defer #261, #227 | Carried from prior sessions; CodeScene sole failure |
| Session report drafts (pc) | **This session** | Defer #1188, #1191 | Cursor-agent draft artifacts; consolidated into 2026-06-09 report |
| Workflow automation (pc) | **None** | Escalate #1193 | Trust boundary on PR automation toolchain |

No zero-diff PRs detected. No stale (>30d) PRs in scope.
| Hydrograph Bolt perf salvage | **#241** (v2 draft) | Close #227 | #227 went `DIRTY` after `main` gained `_create_chart_metadata` / `_save_generated_chart`; v2 uses intent files only (Lesson 0cd) |
| Session doc artifacts (personal-config) | **This session branch** | Defer #1196, #1191, #1188 | Overlapping `tasks/pr-*` files; consolidated into 2026-06-09 report |
| Seatek scanner perf salvage | **#261** | (none) | Carried tail; CodeScene sole failure — human merge decision |
| Jules Palette spinner (personal-config) | **#1197** | Defer to Phase 1 | Not conflicted; MERGEABLE with substantive checks green |

No semantic duplicates among active bot queues. ctrld-sync, email-security-pipeline, and series_correction have zero open PRs.
| Palette EOF (email-security-pipeline) | **#1050** | Close #1049 | Byte-identical diff (`app_runner.py`, `setup_wizard.py`, `ui.py`, `.jules/palette.md`); #1050 is newer Jules session branch |
| Bolt perf (ctrld-sync) | **#877** | (none) | Single open Bolt PR; no overlap with #875 (docs-only QA) |
| Salvage session docs (personal-config) | **This session branch** | Defer #1185 | Overlapping `tasks/pr-*` artifacts; Salvage Agent owns draft salvage PRs |
| Perf salvage drafts (sa/hg) | **None** | Defer #261, #227 | Carried from prior sessions; CodeScene sole failure |

No other semantic duplicates among merge candidates.

## Session dispositions (executed)

| Disposition | PRs | Count |
| --- | --- | ---: |
| **CLOSE-DUPLICATE** | esp #1053 | 1 |
| **CLOSE-ZERO-DIFF** | pc #1189 | 1 |
| **CLOSE-SUPERSEDED** | pc #1185 | 1 |
| **DEFER** | sa #261; hg #227 | 2 |
| **PHASE1-HANDOFF** | esp #1054; scp #102; pc #1190 | 3 |
| **MERGE** | sc #102; hg #237; esp #1054, #1056, #1058, #1060; pc #1190, #1195; sa #270; ctrld #879 | 10 |
| **CLOSE-ZERO-DIFF** | — | 0 |
| **DEFER** | pc #1191, #1188; sa #261; hg #227 | 4 |
| **ESCALATE** | pc #1193 | 1 |
| **SALVAGE** (new draft) | hg #241 | 1 |
| **CLOSE-SUPERSEDED** | hg #227 | 1 |
| **DEFER** | pc #1197; pc #1196, #1191, #1188; sa #261 | 5 |
| **MERGE** | ctrld #875, #877; esp #1050, #1052 | 4 |
| **CLOSE-DUPLICATE** | esp #1049 | 1 |
| **DEFER** | pc #1185; sa #261; hg #227 | 3 |
| **ESCALATE** | — | 0 |

## Security gate review

| PR | Tier | Gate result | Notes |
| --- | --- | --- | --- |
| scp #102 | T1 SECURITY | PASS | Removes `traceback.format_exc()` from user-facing output in `generate_overview_table.py` |
| esp #1054 | T3 REFACTOR | PASS | Test-only unused import removal |
| pc #1190 | T3 UI | PASS (pending Swift) | CSS contrast tokens only; security suite green except in-progress Swift CodeQL |
| pc #1189 | CI/INFRA | N/A | Zero-diff — closed without merge |

## CodeScene advisory failures (not security blockers)

Deferred #261, #227: salvage perf PRs where CodeScene is sole failure (unchanged since 2026-06-03).

## Infra-broken main check (Lesson 0t)

No repo-wide infra breakage detected. ctrld-sync queue is empty. No `CONFLICTING` bot PRs remain.
| sc #102 | SECURITY | PASS | Removes `traceback.print_exc()` — reduces info disclosure; no new attack surface |
| hg #237 | SECURITY | PASS | Adds `sanitize_filename()` on `river_mile` path component; defense-in-depth |
| esp #1058 | PERFORMANCE | PASS | `Counter` dedup in spam URL scoring; preserves score semantics via `count` multiplier |
| esp #1056 | UI | PASS | `Colors.colorize()` replaces raw ANSI escapes; no auth/secrets |
| esp #1060 | REFACTOR | PASS | Request timeouts on CodeScene API calls; formatting only in threat-detection paths |
| pc #1190 | UI | PASS | Status color contrast in analytics dashboard shell script |
| pc #1195 | PERFORMANCE | PASS | Hoists `datetime.strptime` out of loop; no input-path changes |
| sa #270 | PERFORMANCE | PASS | Pre-compiles regex patterns in scanner; no logic change |
| ctrld #879 | CI/INFRA | PASS | Docs-only QA matrix update |
| pc #1193 | CI/INFRA | DEFER | Workflow pin on automation toolchain — human review required |

## CodeScene advisory failures (not security blockers)

Deferred #261, #227: salvage perf PRs where CodeScene is sole failure (unchanged tail from 2026-06-06/07).
| hg #241 | T3 perf salvage | PASS (local) | `data_loader.py` / `processor.py` only; pytest subset 26/26 green; GitGuardian green on push |
| hg #227 | — | N/A | Closed — conflicted branch superseded |
| sa #261 | T3 perf salvage | PASS (security) | lint-and-test, CodeQL, GitGuardian green; CodeScene advisory only |
| pc #1197 | UI | PASS | Spinner UX in non-TTY; tests green; no secrets/auth surface |

## CodeScene advisory failures (not security blockers)

- **sa #261**: scanner perf salvage — sole CodeScene failure (unchanged 5d tail).
- **hg #241**: awaiting CI; prior #227 had same pattern (Lesson 0ce contrast for perf vs security).

## Infra-broken main check (Lesson 0t)

No repo-wide infra breakage detected. Four repos have zero open PRs. Hydrograph conflict was branch drift on a stale salvage base, not `main` CI failure.

## Salvage decision tree outcomes

| Repo | PR | Tree outcome | Action |
| --- | ---: | --- | --- |
| Hydrograph | #227 | Conflict + valuable diff on intent files | v2 salvage branch; close original |
| Seatek | #261 | MERGEABLE; value retained; advisory CI | Defer for human review |
| personal-config | #1197 | Not in salvage queue (clean, not conflicted) | Hand off to Phase 1 |
| ctrld #875 | CI/INFRA | PASS | Docs-only QA matrix update |
| ctrld #877 | PERFORMANCE | PASS | Counting optimization in plan builder; no auth/API changes |
| esp #1050 | UI | PASS | EOF→KeyboardInterrupt translation; terminal reset in `finally`; no secrets |
| esp #1052 | PERFORMANCE | PASS | Pre-lowercase + case-sensitive regex; preserves ReDoS-safe patterns; spam scoring path only |
| esp #1049 | UI | N/A | Closed as duplicate before merge |

## CodeScene advisory failures (not security blockers)

Deferred #261, #227: salvage perf PRs where CodeScene is sole failure (unchanged tail, fourth consecutive session).

## Infra-broken main check (Lesson 0t)

No repo-wide infra breakage detected. All merge candidates had green required security/test gates.

## Merge sequencing notes

- #1052 first merge attempt failed with **Base branch was modified** after #1050 merged; resolved via `update-branch` + CI re-run (Lesson 0c).
