# PR Triage — Phase 2 Salvage 2026-08-12

## Decision summary

| Repo | PR | Disposition | Action |
| ---- | -- | ----------- | ------ |
| Hydrograph… | 504 | SALVAGE | Draft [#507](https://github.com/abhimehro/Hydrograph_Versus_Seatek_Sensors_Project/pull/507); close #504 |
| ctrld-sync | 1150 | SALVAGE | Draft [#1159](https://github.com/abhimehro/ctrld-sync/pull/1159); strip lock/deps; close #1150 |
| repoprompt-ce | 224 | SALVAGE | Draft [#237](https://github.com/abhimehro/repoprompt-ce/pull/237) tests-only (0fj); close #224 |
| series… | 378 | CLOSE no-op | Target `dummy_todos.py` gone from main; no auth re-intro |
| repoprompt-ce | 231 | HOLD/ESCALATE | DateFormatter + contamination (0fm); comment only |
| personal-config | 1977 | DOCS recover | Fold Phase 1 reports into Phase 2 docs PR; close #1977 |
| personal-config | 1907 | ESCALATE | CORS trust boundary — human |
| ctrld-sync | 1156 | ESCALATE | TOCTOU plan JSON — human |
| ctrld-sync | 1136 | ESCALATE | mypy 2.x major — human |
| email-security-pipeline | 1444 | ESCALATE | opencv 5.x + failing CI (S6) |
| Seatek_Analysis | 657 | REQUEST_CHANGES | fail-open OSError→{} |
| Seatek_Analysis | 643 | DEFER | CodeScene/CodeQL |
| Hydrograph… | 498 | DEFER | failing tests + junk |
| series… | 386/385 | ESCALATE | pandas/numpy majors + failing CI |
| series… | 375 | DEFER | CodeScene salvage test |
| repoprompt-ce | 232/228 | ESCALATE | TOCTOU contaminated |
| repoprompt-ce | 226 | REQUEST_CHANGES | a11y scope creep |
| repoprompt-ce | 235/234/227 | DEFER | failing CI / contaminated salvage |

## Human merge priority (drafts)

1. Hydro [#507](https://github.com/abhimehro/Hydrograph_Versus_Seatek_Sensors_Project/pull/507) — sanitize newline tests
2. ctrld [#1159](https://github.com/abhimehro/ctrld-sync/pull/1159) — dry-run pluralize (0fm-compliant `sync_results` count)
3. rpce [#237](https://github.com/abhimehro/repoprompt-ce/pull/237) — REPLInputParserTests (`make dev-test FILTER=REPLInputParserTests`)
4. Prior queue: series [#375](https://github.com/abhimehro/series_correction_project_updated/pull/375), rpce [#227](https://github.com/abhimehro/repoprompt-ce/pull/227) (contaminated — prefer fresh re-roll)

## Rules applied

- S1 no autonomous merges
- 0y journal append-only
- 0fj contaminated salvage → fresh main + unique files
- 0fm dry-run error_count from `sync_results`
- 0fn do not re-apply rejected insecure / do not resurrect deleted auth demos
- 0fk one competing `tasks/*` docs lineage
- 0ew skip `request_reviewers` when author is abhimehro
# PR triage — 2026-08-16

## Merge this session (squash)

| PR | Why |
| --- | --- |
| ctrld-sync#1176 | Dev ruff patch 0.16.1→0.16.2 + lock |
| ctrld-sync#1175 | Dev pre-commit patch 4.6.1→4.6.2 + lock (after #1176) |
| ctrld-sync#1173 | Test-only PlanRuleGroup / list[int] annotation (superset of OOS #1165) |
| Hydrograph#521 | requirements.txt numpy pin aligned to pyproject 2.5.2 |
| personal-config#1984 | `draft_fixes` membership → set(); approved; no junk |
| personal-config#2008 | SHA-pinned trufflehog v3.97.0 + codeql-action v4.37.7 |
| email-security-pipeline#1471 | SHA-pinned upload-sarif codeql-bundle-v2.26.3 |
| repoprompt-ce#242 | Docs CoC link + version.env 1.3.0 already on main |
| repoprompt-ce#256 | accessibilityLabel on three icon-only controls; CLEAN macos-26 CI |

## Close this session

| PR | Why |
| --- | --- |
| series#398 | Zero-diff daily QA (0 files) |
| personal-config#2011 | Duplicate of merged #1984 (+ future-dated bolt.md) |

## Duplicate / overlap groups (keep one later)

| Group | Keep | Close/defer rest |
| --- | --- | --- |
| pc draft_fixes set() | **#1984 merged** | #2011 closed |
| pc str.join flip-flop | none (HOLD 0fo) | #1996, #1978, DIRTY #1997/#1985 |
| rpce Palette a11y | **#256 merged**; #247 after junk strip | #253 red CI |
| rpce TOCTOU writes | Phase 2 newest unique (#254) | #250, #243, #239 |
| rpce DateFormatter cache | Phase 2 | #257, #249, #241, #236 |
| hg path traversal | Phase 2 combined | #524, #520, salvage #507 |
| seatek file-read DoS / yaml | Phase 2 combined (toolchain scripts) | #680, #676, #667, #665, #662, #657 |
| pc CWE-88 pgrep | Phase 2 | DIRTY #2000, #1989 |
| ctrld mypy tests | **#1173 merged** | #1165 human OOS leftover |

## HOLD (request-changes / comment)

- ctrld#1161 — 0fo: inverts generator `sum()` benchmark guard
- ctrld#1170 — floating `setup-cli@v0.86.2` in generated gh-aw file
- ctrld#1162 — ruff pre-commit pin 0.16.1 after #1176 landed 0.16.2 (lesson **0fs**)
- hg#523 — `pr_body.txt` tracked junk (0fg)
- seatek#673 — `# nolint next` split across wrapped lines
- seatek#681 — duplicate backdated bolt.md; adversarial split → fail-secure HOLD
- pc#1996/#1978 — join generator↔list thrash overlapping merged #1984
- rpce#247 — good Swift hunk + stray `patch_formatter.py`
- series#390 — sanitizer `copy(deep=False)` (0fp)
- pc#1991 — unescaped HTML empty-state (prior HOLD)
- pc#1982 — yaml soft-import fail-open (prior HOLD)

## ESCALATE (security / majors / toolchain)

Sentinel/CORS/TOCTOU/CWE, Dependabot majors with red CI, repo-health that
rewrites install posture (`esp#1473`), and `.github/scripts/repository_automation*`
(`seatek#679` and DoS cluster). CodeScene trigger posted on **ctrld#1183** and
**pc#1980**.

## OOS human

- personal-config#1969 skill-index workflow
- ctrld-sync#1165 (leave; may become zero-diff vs merged #1173)

## No stale (>30d) PRs this inventory
