# PR Triage — 2026-08-18 (Phase 2 salvage)

Live CONFLICTING: **13**. Auth: `abhimehro` PAT. **S1 never merge.**

## Decision summary

### ctrld uv Docker/Bandit (#1188)

Jules `requirements.txt` + Docker/bandit. `requirements.txt` already on main.
Action: **SALVAGE** Docker/bandit + repair corrupted `uses:` → draft
[#1194](https://github.com/abhimehro/ctrld-sync/pull/1194). **CLOSE** #1188.

### ctrld is_valid_rule (#1174)

Copilot patched deleted `sync.py`. Canonical home: `sync/rules.py`. Action:
**SALVAGE** adapted helper → draft
[#1195](https://github.com/abhimehro/ctrld-sync/pull/1195). **CLOSE** #1174.
Lesson **0fv**.

### pc pgrep CWE-88 (#2000/#1989)

Jules/Copilot `pgrep -x --`. Action: **SALVAGE** → draft
[#2022](https://github.com/abhimehro/personal-config/pull/2022). **CLOSE** both.

### pc Bolt join (#1997/#1985)

Both superseded by CLEAN
[#1996](https://github.com/abhimehro/personal-config/pull/1996). **CLOSE**.

### pc Palette (#1991 vs #1980)

#1980 already has unique `get_palette_state.sh` + tests. **CLOSE** #1991.

### pc eval→shopt (#2007)

Jules eval-removal is CLEAN. Copilot unquoted restore is **0fu**. **ESCALATE**
(do not salvage).

### pc CORS (#1907)

Mega + allowlist. **ESCALATE**.

### ctrld HOLD (#1161)

Retry wrapper. **HOLD** 0fo.

### ctrld mypy 2.x (#1136)

**ESCALATE**.

### esp Daily QA (#1495)

Zero unique vs main. **CLOSE** 0fr.

### esp headers (#1487)

Already on main. **CLOSE**.

### esp requirements-ci (#1473)

**ESCALATE**.

### seatek POSIXct (#690)

One unique `.POSIXct` line; rest contamination. **SALVAGE** → draft
[#693](https://github.com/abhimehro/Seatek_Analysis/pull/693). **CLOSE** #690.

---

# PR Triage — 2026-08-13 (Phase 2 salvage)

Live CONFLICTING: **none**. Triage is duplicate / contamination / security-gate.

# PR Triage — Phase 2 Salvage 2026-08-12

## Decision summary

### rpce TOCTOU cluster

PRs: [#239](https://github.com/abhimehro/repoprompt-ce/pull/239) (focused, 3
files), [#232](https://github.com/abhimehro/repoprompt-ce/pull/232) (~290 files,
−27k), [#228](https://github.com/abhimehro/repoprompt-ce/pull/228) (same mega).
Action: **CLOSE** #232/#228 as superseded by #239. **ESCALATE** #239 (T1; Style
red; `nonisolated` not involved). Do not merge autonomously.

### rpce DateFormatter cluster

PRs: [#236](https://github.com/abhimehro/repoprompt-ce/pull/236) (GitService
only, `nonisolated(unsafe)` static ISO8601),
[#241](https://github.com/abhimehro/repoprompt-ce/pull/241) (6 files),
[#231](https://github.com/abhimehro/repoprompt-ce/pull/231) (−27k contaminated).
Action: **CLOSE** #231. **HOLD** #236/#241 (concurrency).

### rpce Palette a11y

[#235](https://github.com/abhimehro/repoprompt-ce/pull/235) focused CLEAN vs
[#226](https://github.com/abhimehro/repoprompt-ce/pull/226) 60-file rewrite.
Action: **CLOSE** #226. Human squash #235.

### rpce MCP tests (#227 vs #237 vs main)

[#227](https://github.com/abhimehro/repoprompt-ce/pull/227) 51 files.
`NewlineDelimitedSocketReaderTests.swift` **byte-identical** to main.
`REPLInputParserTests.swift` already covered by
[#237](https://github.com/abhimehro/repoprompt-ce/pull/237) / main. Unique:
`MCPCommandParserTests.swift` (parser APIs exist on main; no test class).
Action: **SALVAGE** parser tests only; **CLOSE** #227.

### personal-config Bolt join / set lookup

[#1984](https://github.com/abhimehro/personal-config/pull/1984) `set()` —
merge-ready. [#1985](https://github.com/abhimehro/personal-config/pull/1985)
join() + yaml `skipIf` fail-open.
[#1978](https://github.com/abhimehro/personal-config/pull/1978) join() + journal
prepend. [#1982](https://github.com/abhimehro/personal-config/pull/1982) yaml
skipIf only. Action: **HOLD** #1985/#1978/#1982 (0fo/fail-open). Do not salvage
yaml skip.

### series sanitizer / pandas majors

[#390](https://github.com/abhimehro/series_correction_project_updated/pull/390)
`copy(deep=False)` — REQUEST_CHANGES (0fp).
[#386](https://github.com/abhimehro/series_correction_project_updated/pull/386)
/
[#385](https://github.com/abhimehro/series_correction_project_updated/pull/385)
majors — ESCALATE.
[#375](https://github.com/abhimehro/series_correction_project_updated/pull/375)
rewrites entire `test_batch_correction.py` — **CLOSE** (0fj); OSError coverage
already on main for data-dir create.

## Zero-diff CLOSE

Seatek [#664](https://github.com/abhimehro/Seatek_Analysis/pull/664), rpce
[#240](https://github.com/abhimehro/repoprompt-ce/pull/240),
[#234](https://github.com/abhimehro/repoprompt-ce/pull/234), series
[#384](https://github.com/abhimehro/series_correction_project_updated/pull/384).

## Security gate — never salvage-merge

- CORS: pc [#1907](https://github.com/abhimehro/personal-config/pull/1907)
- Sentinel SSRF: pc
  [#1980](https://github.com/abhimehro/personal-config/pull/1980)
- Skill-index / Gitleaks-adjacent: pc
  [#1969](https://github.com/abhimehro/personal-config/pull/1969)
- TOCTOU: ctrld [#1156](https://github.com/abhimehro/ctrld-sync/pull/1156); rpce
  #239
- Sentinel: Seatek
  [#665](https://github.com/abhimehro/Seatek_Analysis/pull/665),
  [#662](https://github.com/abhimehro/Seatek_Analysis/pull/662),
  [#657](https://github.com/abhimehro/Seatek_Analysis/pull/657)
- Majors: ctrld [#1136](https://github.com/abhimehro/ctrld-sync/pull/1136) mypy
  2.x; esp
  [#1444](https://github.com/abhimehro/email-security-pipeline/pull/1444) opencv
  5.x; Seatek [#661](https://github.com/abhimehro/Seatek_Analysis/pull/661)
  numpy 2.5 in venv pin; series #386/#385
- Security-classified repo pytest: esp #1444 (Lesson 0bb)

## Stale (>30 days)

None in the auto inventory.

| Repo                    | PR          | Disposition     | Action                                                                                                   |
| ----------------------- | ----------- | --------------- | -------------------------------------------------------------------------------------------------------- |
| Hydrograph…             | 504         | SALVAGE         | Draft [#507](https://github.com/abhimehro/Hydrograph_Versus_Seatek_Sensors_Project/pull/507); close #504 |
| ctrld-sync              | 1150        | SALVAGE         | Draft [#1159](https://github.com/abhimehro/ctrld-sync/pull/1159); strip lock/deps; close #1150           |
| repoprompt-ce           | 224         | SALVAGE         | Draft [#237](https://github.com/abhimehro/repoprompt-ce/pull/237) tests-only (0fj); close #224           |
| series…                 | 378         | CLOSE no-op     | Target `dummy_todos.py` gone from main; no auth re-intro                                                 |
| repoprompt-ce           | 231         | HOLD/ESCALATE   | DateFormatter + contamination (0fm); comment only                                                        |
| personal-config         | 1977        | DOCS recover    | Fold Phase 1 reports into Phase 2 docs PR; close #1977                                                   |
| personal-config         | 1907        | ESCALATE        | CORS trust boundary — human                                                                              |
| ctrld-sync              | 1156        | ESCALATE        | TOCTOU plan JSON — human                                                                                 |
| ctrld-sync              | 1136        | ESCALATE        | mypy 2.x major — human                                                                                   |
| email-security-pipeline | 1444        | ESCALATE        | opencv 5.x + failing CI (S6)                                                                             |
| Seatek_Analysis         | 657         | REQUEST_CHANGES | fail-open OSError→{}                                                                                     |
| Seatek_Analysis         | 643         | DEFER           | CodeScene/CodeQL                                                                                         |
| Hydrograph…             | 498         | DEFER           | failing tests + junk                                                                                     |
| series…                 | 386/385     | ESCALATE        | pandas/numpy majors + failing CI                                                                         |
| series…                 | 375         | DEFER           | CodeScene salvage test                                                                                   |
| repoprompt-ce           | 232/228     | ESCALATE        | TOCTOU contaminated                                                                                      |
| repoprompt-ce           | 226         | REQUEST_CHANGES | a11y scope creep                                                                                         |
| repoprompt-ce           | 235/234/227 | DEFER           | failing CI / contaminated salvage                                                                        |

## Human merge priority (drafts)

1. Hydro
   [#507](https://github.com/abhimehro/Hydrograph_Versus_Seatek_Sensors_Project/pull/507)
   — sanitize newline tests
2. ctrld [#1159](https://github.com/abhimehro/ctrld-sync/pull/1159) — dry-run
   pluralize (0fm-compliant `sync_results` count)
3. rpce [#237](https://github.com/abhimehro/repoprompt-ce/pull/237) —
   REPLInputParserTests (`make dev-test FILTER=REPLInputParserTests`)
4. Prior queue: series
   [#375](https://github.com/abhimehro/series_correction_project_updated/pull/375),
   rpce [#227](https://github.com/abhimehro/repoprompt-ce/pull/227)
   (contaminated — prefer fresh re-roll)

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

| PR                           | Why                                                                    |
| ---------------------------- | ---------------------------------------------------------------------- |
| ctrld-sync#1176              | Dev ruff patch 0.16.1→0.16.2 + lock                                    |
| ctrld-sync#1175              | Dev pre-commit patch 4.6.1→4.6.2 + lock (after #1176)                  |
| ctrld-sync#1173              | Test-only PlanRuleGroup / list[int] annotation (superset of OOS #1165) |
| Hydrograph#521               | requirements.txt numpy pin aligned to pyproject 2.5.2                  |
| personal-config#1984         | `draft_fixes` membership → set(); approved; no junk                    |
| personal-config#2008         | SHA-pinned trufflehog v3.97.0 + codeql-action v4.37.7                  |
| email-security-pipeline#1471 | SHA-pinned upload-sarif codeql-bundle-v2.26.3                          |
| repoprompt-ce#242            | Docs CoC link + version.env 1.3.0 already on main                      |
| repoprompt-ce#256            | accessibilityLabel on three icon-only controls; CLEAN macos-26 CI      |

## Close this session

| PR                   | Why                                                |
| -------------------- | -------------------------------------------------- |
| series#398           | Zero-diff daily QA (0 files)                       |
| personal-config#2011 | Duplicate of merged #1984 (+ future-dated bolt.md) |

## Duplicate / overlap groups (keep one later)

| Group                       | Keep                                   | Close/defer rest                   |
| --------------------------- | -------------------------------------- | ---------------------------------- |
| pc draft_fixes set()        | **#1984 merged**                       | #2011 closed                       |
| pc str.join flip-flop       | none (HOLD 0fo)                        | #1996, #1978, DIRTY #1997/#1985    |
| rpce Palette a11y           | **#256 merged**; #247 after junk strip | #253 red CI                        |
| rpce TOCTOU writes          | Phase 2 newest unique (#254)           | #250, #243, #239                   |
| rpce DateFormatter cache    | Phase 2                                | #257, #249, #241, #236             |
| hg path traversal           | Phase 2 combined                       | #524, #520, salvage #507           |
| seatek file-read DoS / yaml | Phase 2 combined (toolchain scripts)   | #680, #676, #667, #665, #662, #657 |
| pc CWE-88 pgrep             | Phase 2                                | DIRTY #2000, #1989                 |
| ctrld mypy tests            | **#1173 merged**                       | #1165 human OOS leftover           |

## HOLD (request-changes / comment)

- ctrld#1161 — 0fo: inverts generator `sum()` benchmark guard
- ctrld#1170 — floating `setup-cli@v0.86.2` in generated gh-aw file
- ctrld#1162 — ruff pre-commit pin 0.16.1 after #1176 landed 0.16.2 (lesson
  **0fs**)
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
rewrites install posture (`esp#1473`), and
`.github/scripts/repository_automation*` (`seatek#679` and DoS cluster).
CodeScene trigger posted on **ctrld#1183** and **pc#1980**.

## OOS human

- personal-config#1969 skill-index workflow
- ctrld-sync#1165 (leave; may become zero-diff vs merged #1173)

## No stale (>30d) PRs this inventory
