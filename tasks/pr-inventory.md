# PR Inventory — 2026-08-08

Session: Phase 1 cron | Preflight PASS 7/7 | Branch `cursor-agent/automated-pr-workflow-d318`

| Repo | PR | Author | Category | CI | Conflicts | Age (upd) | Disposition |
| ---- | -- | ------ | -------- | -- | --------- | --------- | ----------- |
| personal-config | 1903 | abhimehro | REFACTOR | green | CLEAN | 08-06 | MERGE |
| personal-config | 1907 | abhimehro | SECURITY | green | CLEAN | 08-07 | ESCALATE CORS |
| personal-config | 1935 | abhimehro | CI/INFRA | green | CLEAN | 08-06 | MERGE (trufflehog FP) |
| personal-config | 1938 | abhimehro | FEATURE | green | CLEAN | 08-08 | MERGE (salvage tests) |
| personal-config | 1939 | cursor | CI/INFRA | — | CONFLICTING | 08-08 | DEFER draft salvage docs |
| personal-config | 1941 | abhimehro | CI/INFRA | green | CLEAN | 08-07 | CLOSE twin of #1935 |
| personal-config | 1943 | abhimehro | UI | green | CLEAN | 08-07 | MERGE Palette |
| personal-config | 1945 | abhimehro | PERFORMANCE | green | CLEAN | 08-08 | MERGE Bolt |
| ctrld-sync | 1128 | abhimehro | REFACTOR | green | CLEAN | 08-06 | DEFER (main.py+docs format; after #1138) |
| ctrld-sync | 1133 | dependabot | DEPENDENCY | unstable label | CLEAN | 08-07 | DEFER lock sibling (pre-commit) |
| ctrld-sync | 1134 | dependabot | DEPENDENCY | green | CLEAN | 08-07 | MERGE pytest lock (one/session) |
| ctrld-sync | 1135 | dependabot | DEPENDENCY | unstable draft | CLEAN | 08-07 | DEFER lock sibling (ruff) |
| ctrld-sync | 1136 | dependabot | DEPENDENCY | fail label | CLEAN | 08-07 | ESCALATE mypy 2.x major |
| ctrld-sync | 1138 | abhimehro | UI | green | CLEAN | 08-07 | MERGE Palette |
| ctrld-sync | 1139 | abhimehro | REFACTOR | green | CLEAN | 08-07 | DEFER main.py format vs #1128 |
| email-security-pipeline | 1421 | abhimehro | PERFORMANCE | — | CONFLICTING | 08-07 | ESCALATE/DEFER CodeScene+conflict |
| email-security-pipeline | 1437 | abhimehro | PERFORMANCE | green | CLEAN | 08-08 | ESCALATE sanitizer regression |
| email-security-pipeline | 1444 | dependabot | DEPENDENCY | fail | CLEAN | 08-07 | ESCALATE opencv 5.x |
| email-security-pipeline | 1447 | abhimehro | UI | CodeScene fail | CLEAN | 08-07 | REQUEST_CHANGES + CS trigger |
| email-security-pipeline | 1449 | abhimehro | PERFORMANCE | green | CLEAN | 08-08 | MERGE Bolt |
| Seatek_Analysis | 573–627 | abhimehro | SECURITY | green* | CLEAN | 08-07 | ESCALATE Sentinel cluster |
| Seatek_Analysis | 617 | abhimehro | SECURITY | green | CLEAN | 08-07 | CLOSE zero-diff |
| Seatek_Analysis | 620 | abhimehro | SECURITY | green | CLEAN | 08-07 | ESCALATE cluster head |
| Seatek_Analysis | 623 | abhimehro | PERFORMANCE | green | CLEAN | 08-07 | CLOSE twin of #628 |
| Seatek_Analysis | 626 | abhimehro | CI/INFRA | green | CLEAN | 08-07 | CLOSE zero-diff |
| Seatek_Analysis | 628 | abhimehro | PERFORMANCE | green | CLEAN | 08-08 | MERGE Bolt sprintf |
| Hydrograph… | 459–488 | abhimehro | SECURITY | green | CLEAN | 08-07 | ESCALATE sanitize_filename cluster |
| series_correction… | 364 | abhimehro | SECURITY | green | CLEAN | 08-07 | ESCALATE PBKDF2 |
| series_correction… | 365 | abhimehro | SECURITY | green | CLEAN | 08-07 | ESCALATE auth timing |
| series_correction… | 369 | abhimehro | FEATURE | green | UNSTABLE | 08-07 | DEFER salvage tests |
| series_correction… | 371 | abhimehro | REFACTOR | green | CLEAN | 08-07 | MERGE Jules format |
| series_correction… | 372 | abhimehro | SECURITY | CodeScene | CLEAN | 08-07 | REQUEST_CHANGES + CS |
| series_correction… | 374 | abhimehro | REFACTOR | CodeScene | CLEAN | 08-07 | REQUEST_CHANGES + CS |
| repoprompt-ce | 184 | abhimehro | FEATURE | shard1 fail | UNSTABLE | 08-06 | REQUEST_CHANGES |
| repoprompt-ce | 186/187/194 | abhimehro | FEATURE | — | CLEAN | 08-07 | DEFER large test suites |
| repoprompt-ce | 196/201/210/214 | abhimehro | SECURITY | — | CLEAN | 08-07 | ESCALATE TOCTOU cluster |
| repoprompt-ce | 206 | abhimehro | PERFORMANCE | green | CLEAN | 08-08 | MERGE salvage indexBytes |
| repoprompt-ce | 207 | abhimehro | SECURITY | green | CLEAN | 08-08 | MERGE salvage stderr bytes |
| repoprompt-ce | 212 | abhimehro | PERFORMANCE | green | CLEAN | 08-07 | MERGE DateFormatter |
| repoprompt-ce | 213 | abhimehro | UI | green | CLEAN | 08-08 | MERGE a11y salvage |
| repoprompt-ce | 216 | abhimehro | PERFORMANCE | shard4 fail | UNSTABLE | 08-08 | CLOSE twin/#212 prefer |

\*Sentinel cluster CI not individually re-verified this session; held per policy.

---

## Phase 2 addendum (2026-08-08)

# PR Inventory — Phase 2 Salvage 2026-08-08

Preflight: PASS 7/7 (+ `make cursor-cloud-hooks`). Auth: `abhimehro` PAT (0ew).
Source: Phase 1 [`pr-review-2026-08-08.md`](pr-review-2026-08-08.md) / [#1946](https://github.com/abhimehro/personal-config/pull/1946) remainder + live CONFLICTING re-fetch.

## Open counts (live)

| Repo | Open | CONFLICTING | Notes |
|------|-----:|------------:|-------|
| personal-config | 2 | 0 | #1946 docs draft; #1907 CORS CLEAN |
| ctrld-sync | 4 | 0 | #1136 mypy major; #1133/#1135 deps |
| email-security-pipeline | 3 | 1 | #1421 aiohttp DIRTY; #1444 opencv; #1447 Palette |
| Seatek_Analysis | 12 | 0 | Sentinel path-hijack cluster |
| Hydrograph… | 11 | 0 | sanitize_filename cluster |
| series_correction… | 4 | 1 | #364 PBKDF2 DIRTY; #365/#372 |
| repoprompt-ce | 8 | 1 | #196 TOCTOU DIRTY; TOCTOU/test cluster |

## CONFLICTING queue (start → disposition)

| Repo | PR | Author/branch signal | Disposition |
|------|---:|----------------------|-------------|
| personal-config | 1939 | cursor salvage docs | CLOSE → recovered into this docs PR (0fk) |
| email-security-pipeline | 1437 | salvage sanitize fast-path | CLOSE rejected (0fl) |
| email-security-pipeline | 1421 | Bolt aiohttp | ESCALATE S6/0fh |
| series… | 369 | prior salvage OSError | SALVAGE → [#375](https://github.com/abhimehro/series_correction_project_updated/pull/375) |
| series… | 374 | Jules black format | CLOSE superseded by #371 |
| series… | 364 | Sentinel PBKDF2 | ESCALATE auth |
| repoprompt-ce | 194 | Jules ToolGroups | SALVAGE → [#218](https://github.com/abhimehro/repoprompt-ce/pull/218) |
| repoprompt-ce | 187 | Jules poll tests | CLOSE superseded (coverage on main) |
| repoprompt-ce | 196 | Sentinel TOCTOU | ESCALATE |

## Auto-resolved since Phase 1 snapshots

- pc #1938 MERGED; #1937 MERGED; rpce #213 MERGED; series #371 MERGED
