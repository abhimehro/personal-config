# PR Triage — 2026-08-13 (Phase 2 salvage)

Live CONFLICTING: **none**. Triage is duplicate / contamination / security-gate.

## Duplicate / overlap groups

### rpce TOCTOU cluster
PRs: [#239](https://github.com/abhimehro/repoprompt-ce/pull/239) (focused, 3
files), [#232](https://github.com/abhimehro/repoprompt-ce/pull/232) (~290 files,
−27k), [#228](https://github.com/abhimehro/repoprompt-ce/pull/228) (same mega).
Action: **CLOSE** #232/#228 as superseded by #239. **ESCALATE** #239 (T1;
Style red; `nonisolated` not involved). Do not merge autonomously.

### rpce DateFormatter cluster
PRs: [#236](https://github.com/abhimehro/repoprompt-ce/pull/236) (GitService
only, `nonisolated(unsafe)` static ISO8601), [#241](https://github.com/abhimehro/repoprompt-ce/pull/241)
(6 files), [#231](https://github.com/abhimehro/repoprompt-ce/pull/231) (−27k
contaminated). Action: **CLOSE** #231. **HOLD** #236/#241 (concurrency).

### rpce Palette a11y
[#235](https://github.com/abhimehro/repoprompt-ce/pull/235) focused CLEAN vs
[#226](https://github.com/abhimehro/repoprompt-ce/pull/226) 60-file rewrite.
Action: **CLOSE** #226. Human squash #235.

### rpce MCP tests (#227 vs #237 vs main)
[#227](https://github.com/abhimehro/repoprompt-ce/pull/227) 51 files.
`NewlineDelimitedSocketReaderTests.swift` **byte-identical** to main.
`REPLInputParserTests.swift` already covered by [#237](https://github.com/abhimehro/repoprompt-ce/pull/237)
/ main. Unique: `MCPCommandParserTests.swift` (parser APIs exist on main; no
test class). Action: **SALVAGE** parser tests only; **CLOSE** #227.

### personal-config Bolt join / set lookup
[#1984](https://github.com/abhimehro/personal-config/pull/1984) `set()` — merge-ready.
[#1985](https://github.com/abhimehro/personal-config/pull/1985) join() + yaml
`skipIf` fail-open. [#1978](https://github.com/abhimehro/personal-config/pull/1978)
join() + journal prepend. [#1982](https://github.com/abhimehro/personal-config/pull/1982)
yaml skipIf only. Action: **HOLD** #1985/#1978/#1982 (0fo/fail-open). Do not
salvage yaml skip.

### series sanitizer / pandas majors
[#390](https://github.com/abhimehro/series_correction_project_updated/pull/390)
`copy(deep=False)` — REQUEST_CHANGES (0fp). [#386](https://github.com/abhimehro/series_correction_project_updated/pull/386)
/ [#385](https://github.com/abhimehro/series_correction_project_updated/pull/385)
majors — ESCALATE. [#375](https://github.com/abhimehro/series_correction_project_updated/pull/375)
rewrites entire `test_batch_correction.py` — **CLOSE** (0fj); OSError coverage
already on main for data-dir create.

## Zero-diff CLOSE
Seatek [#664](https://github.com/abhimehro/Seatek_Analysis/pull/664), rpce
[#240](https://github.com/abhimehro/repoprompt-ce/pull/240),
[#234](https://github.com/abhimehro/repoprompt-ce/pull/234), series
[#384](https://github.com/abhimehro/series_correction_project_updated/pull/384).

## Security gate — never salvage-merge
- CORS: pc [#1907](https://github.com/abhimehro/personal-config/pull/1907)
- Sentinel SSRF: pc [#1980](https://github.com/abhimehro/personal-config/pull/1980)
- Skill-index / Gitleaks-adjacent: pc [#1969](https://github.com/abhimehro/personal-config/pull/1969)
- TOCTOU: ctrld [#1156](https://github.com/abhimehro/ctrld-sync/pull/1156); rpce #239
- Sentinel: Seatek [#665](https://github.com/abhimehro/Seatek_Analysis/pull/665),
  [#662](https://github.com/abhimehro/Seatek_Analysis/pull/662),
  [#657](https://github.com/abhimehro/Seatek_Analysis/pull/657)
- Majors: ctrld [#1136](https://github.com/abhimehro/ctrld-sync/pull/1136) mypy 2.x;
  esp [#1444](https://github.com/abhimehro/email-security-pipeline/pull/1444) opencv 5.x;
  Seatek [#661](https://github.com/abhimehro/Seatek_Analysis/pull/661) numpy 2.5 in venv pin;
  series #386/#385
- Security-classified repo pytest: esp #1444 (Lesson 0bb)

## Stale (>30 days)
None in the auto inventory.
