# Salvage Session Reports

> Append-only log for Automated PR Salvage & Recovery Agent sessions. Single
> writer: salvage automation only. Do not edit review entries here; review
> writes to `tasks/review-session-reports.md`.

## Entry template

## Run — 2026-08-01

### Input tail

- Source: Phase 1 `tasks/pr-review-2026-08-01.md` remainder + live re-fetch
- Preflight PASS 7/7; `make cursor-cloud-hooks`; PAT as `abhimehro` (0ew)
- Live CONFLICTING focus: pc #1859/#1857/#1825/#1822; ctrld #1081; esp #1399;
  Seatek #568/#555/#560/#554; rpce DIRTY drift cluster
- Auto-resolved vs Phase 1 snapshot: hg #443 CLEAN; series queue empty

### Outcomes

| Repo                    | Old PR | Disposition     | New PR                                                                  | Notes                                                            |
| ----------------------- | -----: | --------------- | ----------------------------------------------------------------------- | ---------------------------------------------------------------- |
| personal-config         |   1857 | SALVAGE + CLOSE | [#1875](https://github.com/abhimehro/personal-config/pull/1875)         | re-roll DIRTY prior salvage                                      |
| personal-config         |   1859 | SALVAGE + CLOSE | [#1876](https://github.com/abhimehro/personal-config/pull/1876)         | empty-state only; keep a11y                                      |
| personal-config         |   1825 | CLOSE / no-op   | —                                                                       | patch3/scratch only                                              |
| personal-config         |   1822 | ESCALATE        | —                                                                       | CORS + huge churn                                                |
| ctrld-sync              |   1081 | SALVAGE + CLOSE | [#1105](https://github.com/abhimehro/ctrld-sync/pull/1105)              | scratch+CI; skip AGENTS churn                                    |
| email-security-pipeline |   1399 | SALVAGE + CLOSE | [#1401](https://github.com/abhimehro/email-security-pipeline/pull/1401) | spam_analyzer only; reject monolith collapse; `/cs-agent` posted |
| Seatek_Analysis         |    554 | SALVAGE + CLOSE | [#576](https://github.com/abhimehro/Seatek_Analysis/pull/576)           | warn_on_default rename                                           |
| Seatek_Analysis         |    568 | ESCALATE        | —                                                                       | path hijack CRITICAL                                             |
| Seatek_Analysis         |    555 | ESCALATE        | —                                                                       | multi-root                                                       |
| Seatek_Analysis         |    560 | REQUEST_CHANGES | —                                                                       | parallelize mixed churn                                          |
| repoprompt-ce           |    158 | ESCALATE        | —                                                                       | TOCTOU + 37k drift                                               |
| Hydrograph…             |      — | AUTO-RESOLVED   | —                                                                       | #443 CLEAN; security CLEAN leave                                 |
| series_correction…      |      — | DRAINED         | —                                                                       | 0 open PRs                                                       |

- Salvage drafts opened: **5**
- Infra-fix drafts: **0**
- Closed via API: **6**
- Autonomous merges: **0** (S1)
- New lesson: **0fc** (reject module-collapse perf PRs)
- `request_reviewers`: skipped (author already abhimehro)

### Verification

- pc #1875: `python3 -m py_compile parse_inventory.py gh_token_env.py`
- pc #1876: `python3 -m unittest tests.test_infuse_media_server` → OK
- ctrld #1105: `uv run pytest tests/ --collect-only` → 364
- esp #1401: `pytest -k spam` → 28 passed
- seatek #576: `pytest tests/test_repository_automation_common.py` → 15 passed

### Handoff

1. Human merge drafts #1875 / #1876 / #1105 / #1401 / #576 (prefer Seatek #571
   before #576)
2. Human T1 security: pc #1822; seatek #568/#555/#573; hg #445/#448/#450; rpce
   #158
3. Re-roll seatek #560 and rpce DIRTY pile as focused drafts
4. Phase 1 follow-up: hg #443/#441 CLEAN; pc #1867 CI; rpce #163/#164 CI

## Run — 2026-07-30

### Input tail

- Source: Phase 1 draft
  [#1832](https://github.com/abhimehro/personal-config/pull/1832) remainder
  (`pr-review-2026-07-30.md`) + live re-fetch
- Preflight PASS 7/7; `make cursor-cloud-hooks`; PAT as `abhimehro` (0ew)
- Live CONFLICTING: pc #1827/#1821/#1820/#1819; Seatek
  #563/#558/#557/#554/#553/#552/#551; series #329/#327/#320/#315/#313; rpce
  #151/#150/#149/#146
- Prior-day: esp #1383 MERGED; hg #434 MERGED; pc #1812 MERGED

### Outcomes

| Repo               |          Old PR | Disposition      | New PR                                                                          | Notes                       |
| ------------------ | --------------: | ---------------- | ------------------------------------------------------------------------------- | --------------------------- |
| personal-config    |            1827 | CLOSE-SUPERSEDED | —                                                                               | pin already in #1828        |
| personal-config    |            1821 | CLOSE / no-op    | —                                                                               | scratch_triage only         |
| personal-config    |            1820 | SALVAGE + CLOSE  | [#1836](https://github.com/abhimehro/personal-config/pull/1836)                 | GraphQL only; no trunk junk |
| personal-config    |            1819 | CLOSE-SUPERSEDED | —                                                                               | prefer CLEAN #1831          |
| personal-config    |            1822 | ESCALATE         | —                                                                               | CORS MCP                    |
| Seatek_Analysis    | 551/553/557/558 | SALVAGE + CLOSE  | [#565](https://github.com/abhimehro/Seatek_Analysis/pull/565)                   | tests + flattened_updates   |
| Seatek_Analysis    |             552 | ESCALATE         | —                                                                               | list-only shell MCP         |
| Seatek_Analysis    |         554/563 | DEFER            | —                                                                               | API rename redesigns        |
| series_correction… |             313 | SALVAGE          | [#332](https://github.com/abhimehro/series_correction_project_updated/pull/332) | setup.py only               |
| series_correction… |             329 | SALVAGE + CLOSE  | [#333](https://github.com/abhimehro/series_correction_project_updated/pull/333) | parse_year_pair tests       |
| series_correction… |             320 | CLOSE            | —                                                                               | junk; prefer #315           |
| series_correction… |             315 | ESCALATE         | —                                                                               | authenticate MCP            |
| series_correction… |             327 | DEFER            | —                                                                               | large extract-helpers       |
| repoprompt-ce      |             151 | CLOSE-SUPERSEDED | —                                                                               | identical to #153           |
| repoprompt-ce      |     146/149/150 | SALVAGE + CLOSE  | [#157](https://github.com/abhimehro/repoprompt-ce/pull/157)                     | combined Swift micro-opts   |
| repoprompt-ce      |             144 | REQUEST_CHANGES  | —                                                                               | shard 4 fail                |

- Salvage drafts opened: **5**
- Infra-fix drafts: **0**
- Closed via API: **8+** (PAT close works — 0ew)
- Autonomous merges: **0** (S1)
- New lesson: **0ey** (combined salvage drafts)
- CodeScene MCP: unavailable; no `/cs-agent` wait required on salvage drafts
- `request_reviewers`: skipped (author already abhimehro)

### Verification

- pc #1836: `python3 -m unittest tests.test_run_merges` → 8 OK
- seatek #565: `pytest` automation tests → 20 OK
- series #333: `pytest -k parse_year_pair` → 4 OK
- series #332: `py_compile setup.py`
- rpce #157: source-only; needs macOS `dev-swift-build`

### Handoff

1. Human merge drafts #1836 / #565 / #332 / #333 / #157
2. Human T1: #1822 CORS, #552 injection, #315 authenticate
3. Human: decide #554/#563/#327 redesigns or re-roll
4. Prefer merge CLEAN #1831 (covers closed #1819)
5. Squash Phase 1 docs draft
   [#1832](https://github.com/abhimehro/personal-config/pull/1832) when ready

## Run — 2026-07-29

### Input tail

- Source: `tasks/pr-review-2026-07-29.md` Phase 1 remainder + live re-fetch
- Preflight PASS 7/7; `make cursor-cloud-hooks`; PAT as `abhimehro` (0ew)
- Live CONFLICTING: **none**
- Prior-day salvages verified MERGED: pc #1804/#1803, cs #1072

### Outcomes

| Repo                    | Old PR | Disposition     | New PR                                                                        | Notes                             |
| ----------------------- | -----: | --------------- | ----------------------------------------------------------------------------- | --------------------------------- |
| email-security-pipeline |   1381 | SALVAGE + CLOSE | [#1383](https://github.com/abhimehro/email-security-pipeline/pull/1383) draft | release-drafter v7.7.0 only       |
| Hydrograph…             |    434 | ESCALATE        | —                                                                             | python ^3.12 floor; MCP comment   |
| repoprompt-ce           |    144 | REQUEST_CHANGES | —                                                                             | unrelated XCTest flake on shard 1 |

- Salvage drafts opened: **1**
- Infra-fix drafts: **0**
- Closed via API: **1** (#1381) — PAT close works (0ew)
- Autonomous merges: **0** (S1)
- New lesson: **0ew** (abhimehro PAT restores create/close)
- `request_reviewers`: 422 when salvage author is `abhimehro` (expected)

### Verification

- Two-dot residual check on #1381 vs `main` → only release-drafter bump
- Local patch of `.github/workflows/release-drafter.yml` from `origin/main`
- rpce failure log: `WorkspaceCodemapLocalGitClassificationTests` busy/cancel

### Handoff

1. Merge draft
   [#1383](https://github.com/abhimehro/email-security-pipeline/pull/1383)
2. Human decide hg
   [#434](https://github.com/abhimehro/Hydrograph_Versus_Seatek_Sensors_Project/pull/434)
3. Re-run/fix rpce [#144](https://github.com/abhimehro/repoprompt-ce/pull/144)
   shard-1
4. Squash Phase 1 docs
   [#1812](https://github.com/abhimehro/personal-config/pull/1812)

## Run — 2026-07-28

### Input tail

- Source: `tasks/pr-review-2026-07-28.md` Phase 1 remainder + live re-fetch
- Preflight PASS 7/7; `unset GH_TOKEN` (0eo); cursor-cloud-hooks synced
- Live CONFLICTING: pc #1800/#1791, cs #1069/#1064, esp #1362, hg #427/#420/#413
- Dropped since Phase 1: pc #1789/#1787/#1786 (merged)

### Outcomes

| Repo                    | Old PR | Disposition      |                                                          New PR | Notes                           |
| ----------------------- | -----: | ---------------- | --------------------------------------------------------------: | ------------------------------- |
| personal-config         |   1800 | SALVAGE          | [#1804](https://github.com/abhimehro/personal-config/pull/1804) | tasks.py only; S2               |
| personal-config         |   1791 | SALVAGE          | [#1803](https://github.com/abhimehro/personal-config/pull/1803) | common.py regex; S2             |
| ctrld-sync              |   1064 | SALVAGE          |      [#1072](https://github.com/abhimehro/ctrld-sync/pull/1072) | surgical; kept #1067; 364 tests |
| ctrld-sync              |   1069 | CLOSE-SUPERSEDED |                                                               — | duplicate of #1067              |
| ctrld-sync              |   1066 | CLOSE-SUPERSEDED |                                                               — | duplicate; CodeScene now green  |
| email-security-pipeline |   1362 | CLOSE-SUPERSEDED |                                                               — | prefer #1370 (0es)              |
| Hydrograph…             |    413 | CLOSE-SUPERSEDED |                                                               — | prefer #418 (0es)               |
| Hydrograph…             |    427 | CLOSE-SUPERSEDED |                                                               — | duplicate of #428               |
| Hydrograph…             |    420 | CLOSE-SUPERSEDED |                                                               — | duplicate of #428               |
| series_correction…      |    293 | CLOSE-SUPERSEDED |                                                               — | duplicate of #299               |
| email-security-pipeline |   1366 | REQUEST_CHANGES  |                                                               — | artifact v7/v8 (0er)            |
| personal-config         |   1792 | REQUEST_CHANGES  |                                                               — | a11y vs #1795                   |

- Salvage drafts opened: **3**
- Infra-fix drafts: **0**
- Autonomous merges: **0** (S1)
- New lesson: **0et** (surgical salvage when changed-in-both)
- CodeScene MCP: unavailable; posted `/cs-agent` trigger on #1072
- API close: still blocked (0eq); dispositions via MCP reviews
- `request_reviewers`: succeeded on salvage drafts #1803/#1804/#1072 →
  `abhimehro`

### Verification

- pc salvages: `python3 -m py_compile` on touched automation scripts
- cs #1072: `uv run pytest tests/` → **364 passed**
- Compared esp/hg dirty PRs vs `origin/main` for supersession evidence

### Handoff

1. Human merge draft #1804/#1803/#1072 → close originals
2. Human close CLOSE-SUPERSEDED list
3. T1 security: #1370, #418, #1784, #1060, Seatek cluster, #295
4. Fix #1366 / #1792

## Run — 2026-07-27

### Input tail

- Source report/snapshot: `tasks/pr-review-2026-07-26.md` (Phase 1 escalated
  remainder) + live GitHub re-fetch
- PRs investigated: 8 Phase-1 remainder + 2 live CONFLICTING (esp#1362, hg#413)
- Dropped: Seatek #521 (merged since Phase 1)

### Outcomes

- Salvage draft PRs opened: **0** (unique security value already on preferred
  CLEAN twins / main)
- Infra-fix draft PRs opened: **0**
- Originals marked CLOSE-SUPERSEDED (MCP review; API close blocked 0eq): esp
  [#1362](https://github.com/abhimehro/email-security-pipeline/pull/1362) →
  prefer
  [#1370](https://github.com/abhimehro/email-security-pipeline/pull/1370) + main
  #1353; hg
  [#413](https://github.com/abhimehro/Hydrograph_Versus_Seatek_Sensors_Project/pull/413)
  → prefer
  [#418](https://github.com/abhimehro/Hydrograph_Versus_Seatek_Sensors_Project/pull/418)
- REQUEST_CHANGES: esp
  [#1366](https://github.com/abhimehro/email-security-pipeline/pull/1366)
  artifact skew (0er)
- ESCALATE left open: cs #1060; Seatek #507/#518/#525; preferred twins
  #1370/#418 for human T1
- CodeScene: `/cs-agent` posted via MCP on ctrld
  [#1066](https://github.com/abhimehro/ctrld-sync/pull/1066)

### Verification status

- Local verify: compared PR diffs vs `origin/main` for app_runner/setup_wizard
  (esp) and utils/security.py (hg); confirmed #1353 already landed app_runner
  fd-only path
- Close API: `closePullRequest` 403 for Cursor app token (Lesson 0eq) — human
  must close
- request_reviewers: cannot request author `abhimehro` on bot-authored PRs

### Handoff

- Maintainer: close #1362 and #413; T1 review #1370 + #418; fix/close #1366;
  pick one Seatek env-filter PR; ack cs#1060
- Session docs: `tasks/pr-inventory.md`, `pr-triage.md`,
  `pr-review-2026-07-27.md`
- Cross-links: Phase 1 `tasks/pr-review-2026-07-26.md`

## Run — 2026-06-21

### Input tail

- Source report/snapshot: `tasks/pr-review-2026-06-21.md` (Phase 1 deferred
  tail) + live GitHub
- PRs investigated: 8 across 4 repos (0 DIRTY at start)

### Outcomes

- Infra-fix draft PRs opened: personal-config
  [#1311](https://github.com/abhimehro/personal-config/pull/1311) (from #1304),
  repoprompt-ce [#29](https://github.com/abhimehro/repoprompt-ce/pull/29)
  (dependency-review.yml)
- Salvage v2 draft PRs opened: repoprompt-ce
  [#28](https://github.com/abhimehro/repoprompt-ce/pull/28) (from #23)
- Originals closed as superseded/no-op: pc#1304, rp#23

### Verification status

- Blocking checks: mashed workflow YAML on `main` (pc + rp); not pytest-blocked
- Local verify: `rg 'uses:.*uses:' .github/workflows/` → 0 matches after fix
  branches
- CodeScene remediation: `/cs-agent` posted on ctrld#932; sc#135 cs-agent from
  Phase 1

### Handoff

- Maintainer actions required: merge T0 drafts pc#1311 + rp#29 first; T1 review
  pc#1310 + rp#28; update-branch rp#24/#25/#27 after rp#29; Phase 1 merge
  esp#1138
- Cross-links: see `tasks/pr-review-2026-06-21.md` Phase 2 section

## Run — 2026-06-19

### Input tail

- Source report/snapshot: `tasks/pr-review-2026-06-16.md` (deferred tail) + live
  GitHub
- PRs investigated: 5 across 2 repos (3 DIRTY at start: pc#1279, pc#1281,
  pc#1280)

### Outcomes

- Salvage draft PRs opened: personal-config
  [#1287](https://github.com/abhimehro/personal-config/pull/1287) (from #1279),
  [#1288](https://github.com/abhimehro/personal-config/pull/1288) (from #1281)
- Infra-fix draft PRs opened: 0
- Originals closed as superseded/no-op: pc#1279, pc#1281, pc#1280

### Verification status

- Blocking checks: none on `main`
- Local verify: `bash -n configs/.config/mole/lib/core/sudo.sh`;
  `python3 -m py_compile scripts/morning-brief/morning-brief.py`
- CodeScene remediation: sc#121 cs-agent posted earlier; no new posts this run

### Handoff

- Maintainer actions required: T1 review pc#1287; T2 review pc#1284 (CLEAN); T3
  review pc#1288; CodeScene tail on sc#121
- Cross-links: see `tasks/pr-review-2026-06-19.md`

## Run — 2026-06-16

### Input tail

- Source report/snapshot: `tasks/pr-review-2026-06-16.md` (Phase 1 morning)
- PRs investigated: 8 across 5 repos (3 DIRTY at start: pc#1262, ctrld#901,
  ctrld#904)

### Outcomes

- Salvage draft PRs opened: ctrld-sync
  [#908](https://github.com/abhimehro/ctrld-sync/pull/908) (from #901 + #904)
- Infra-fix draft PRs opened: 0
- Originals closed as superseded/no-op: ctrld#901, ctrld#904, pc#1262

### Verification status

- Blocking checks: none on `main`
- Local verify: `uv run pytest tests/ -q` — 341 passed on ctrld salvage branch
- CodeScene remediation: `/cs-agent` posted on #908; sc#121 cs-agent completed
  earlier; hg#262 still failing

### Handoff

- Maintainer actions required: review ctrld#908 draft; Phase 1 merge pc#1261
  (now green); T1 review pc#1249; CodeScene tail on sc#121, hg#262
- Cross-links: see `tasks/pr-review-2026-06-16.md`

## Run — 2026-06-15

### Input tail

- Source report/snapshot: `tasks/pr-review-2026-06-14.md`
- PRs investigated: 9 across 7 repos (1 DIRTY at start: hg#257)

### Outcomes

- Salvage draft PRs opened: Hydrograph
  [#262](https://github.com/abhimehro/Hydrograph_Versus_Seatek_Sensors_Project/pull/262)
  (from #257)
- Infra-fix draft PRs opened: 0
- Originals closed as superseded/no-op: hg#257

### Verification status

- Blocking checks: none on `main` (pc #1240 merged since prior session)
- Local verify: `pytest tests/test_app.py` — 13 passed on salvage branch
- CodeScene remediation: hg#257 had prior `/cs-agent`; #262 awaiting fresh
  CodeScene run

### Handoff

- Maintainer actions required: review hg#262 draft; Phase 1 on pc#1254/#1249,
  ctrld#902, esp#1115; CodeScene tail on ctrld#901, sc#121
- Cross-links: see `tasks/pr-review-2026-06-15.md`

## Run — 2026-06-14

### Input tail

- Source report/snapshot: `tasks/pr-review-2026-06-13.md`
- PRs investigated: 16 across 7 repos (3 DIRTY at start)

### Outcomes

- Salvage draft PRs opened: ctrld-sync
  [#899](https://github.com/abhimehro/ctrld-sync/pull/899) (from #898)
- Infra-fix draft PRs opened: 0 (consolidated to existing pc#1240)
- Originals closed as superseded/no-op/Gate 2: pc#1244, pc#1231, pc#1245,
  esp#1109, ctrld#898, sa#261

### Verification status

- Blocking checks: pc `main` still has `NameError: Any` — T0 #1240 pending human
  merge
- CodeScene remediation commands posted: ctrld #899 (`/cs-agent`); hg#257 and
  sc#119 already had cs-agent from prior sessions

### Handoff

- Maintainer actions required: **Merge pc#1240 first**, then Phase 1 on
  pc#1234/#1235/#1242/#1243 and esp#1107/#1111/#1112; review ctrld#899 draft
- Cross-links: see `tasks/pr-review-2026-06-14.md`

## Run — 2026-06-30

### Input tail

- Source report/snapshot: prior memory (2026-06-29 run) + live GitHub re-fetch
- PRs investigated: 48 in-scope open at start; 4 conflicted (pc #1402, #1376;
  esp #1168, #1175); cascade grew to 9 DIRTY during Phase 1 merge burst

### Outcomes

| Repo                    | Old PR    | Disposition      | New PR | Notes                               |
| ----------------------- | --------- | ---------------- | ------ | ----------------------------------- |
| personal-config         | 1402      | SALVAGE          | 1433   | parse_inventory tests               |
| personal-config         | 1424      | SALVAGE          | 1434   | get_duplicates tests                |
| personal-config         | 1397      | SALVAGE          | 1435   | _find_matching_prs tests            |
| personal-config         | 1393      | SALVAGE          | 1436   | create_denylist tests               |
| personal-config         | 1391      | SALVAGE          | 1437   | format_lists error paths            |
| personal-config         | 1407      | SALVAGE          | 1438   | allowlist mocks + .jules/testing.md |
| personal-config         | 1369–1383 | CLOSE-SUPERSEDED | —      | stale session-doc drafts            |
| email-security-pipeline | 1168      | SALVAGE          | 1192   | Palette fallback                    |
| email-security-pipeline | 1175      | SALVAGE          | 1193   | NLP transformer tests               |
| email-security-pipeline | 1191      | SALVAGE          | 1194   | forgiving CLI selection             |

- Salvage draft PRs opened: 9
- Infra-fix draft PRs opened: 0
- Originals closed as superseded/no-op: 15
- Phase 1 merges (same session): 27

### Verification status

- Blocking checks: pc #1398 GitGuardian; pc #1422 CodeScene; esp #1179
  DIRTY+CodeScene
- CodeScene remediation commands posted: pc #1422, esp #1179

### Handoff

- Maintainer actions required:
  1. Review draft salvages pc #1433–#1438 and esp #1192–#1194
  2. Investigate pc #1398 GitGuardian before merge
  3. Re-run Phase 1 after CodeScene remediation on #1422
  4. Salvage or close esp #1179 after cs-agent cycle
- Cross-links: [Session report](tasks/pr-review-2026-06-30.md)

## Run — YYYY-MM-DD

### Input tail

- Source report/snapshot:
- PRs investigated:

### Outcomes

- Salvage draft PRs opened:
- Infra-fix draft PRs opened:
- Originals closed as superseded/no-op:

### Verification status

- Blocking checks:
- CodeScene remediation commands posted
  (`/cs-agent skill:fix-code-health-degradations`):

### Handoff

- Maintainer actions required:
- Cross-links to PRs and comments:

## Run — 2026-06-10

### Input tail

- Source report/snapshot: `tasks/pr-review-2026-06-09.md` post-session remainder
  (#261, #1193, #1197, #241)
- PRs investigated: 9 open across 4 repos (pc 3, ctrld 1, esp 2, sa 2); hg/scp
  queues clear

### Outcomes

| Repo                    | Old PR | Disposition      | New PR | Notes                       |
| ----------------------- | -----: | ---------------- | -----: | --------------------------- |
| personal-config         |   1203 | CLOSE-SUPERSEDED |      — | Phase-1 session doc draft   |
| personal-config         |   1201 | ESCALATE         |      — | refactoring-agent pin bump  |
| ctrld-sync              |    881 | DEFER            |      — | benchmark regression        |
| email-security-pipeline |   1066 | ESCALATE         |      — | workflow pin bump           |
| Seatek_Analysis         |    273 | ESCALATE         |      — | 9 workflow YAML updates     |
| Seatek_Analysis         |    261 | DEFER            |      — | security regression in diff |

- Salvage draft PRs opened: 0
- Infra-fix draft PRs opened: 0
- Originals closed as superseded: 1 (#1203)

### Verification status

- Blocking checks: ctrld #881 benchmark FAIL; sa #261 security controls removed
- CodeScene remediation: sa #261 CodeScene now PASS (prior `/cs-agent` cycle
  resolved advisory)

### Handoff

- Maintainer actions required:
  1. Review escalated workflow PRs (#1201, #1066, #273)
  2. Do not merge sa #261 until `read_file_safe` restored
  3. Close or fix ctrld #881 Bolt list-comp change
  4. Phase 1: merge pc #1204 / esp #1068 once CodeQL completes
- Cross-links: [Session report](tasks/pr-review-2026-06-10.md)

## Run — 2026-06-13

### Input tail

- Source report/snapshot: `tasks/pr-review-2026-06-12.md` deferred tail + live
  GitHub re-fetch
- PRs investigated: 16 across 6 repos (pc 5, ctrld 3, esp 2, sa 4, hg 1, sc 1)

### Outcomes

| Repo                    | Old PR | Disposition      | New PR | Notes                     |
| ----------------------- | -----: | ---------------- | -----: | ------------------------- |
| personal-config         |   1230 | SALVAGE          |   1237 | analytics_dashboard ARIA  |
| email-security-pipeline |   1096 | SALVAGE          |   1107 | ConnectionConfig refactor |
| email-security-pipeline |   1103 | SALVAGE          |   1108 | media_analyzer parallel   |
| ctrld-sync              |    886 | CLOSE-SUPERSEDED |    893 | emoji alignment duplicate |
| Seatek_Analysis         |    283 | CLOSE-SUPERSEDED |      — | shell=False on main       |
| Seatek_Analysis         |    278 | CLOSE-STALE      |      — | deletes merged tests      |
| Seatek_Analysis         |    282 | CLOSE-STALE      |      — | broad conflict            |
| Seatek_Analysis         |    261 | DEFER            |      — | Gate 2 security           |

- Salvage draft PRs opened: 3 (#1237, #1107, #1108)
- Infra-fix draft PRs opened: 0 (existing #1231 flagged T0)
- Originals closed as superseded/no-op: 8

### Verification status

- Blocking checks: pc main test import failure; hg #257 / sc #114 CodeScene
- CodeScene remediation: posted `/cs-agent` on esp #1108

### Handoff

- Maintainer actions required:
  1. **Merge pc #1231 first** (T0 infra-fix)
  2. Review draft salvages #1237, #1107, #1108
  3. Phase 1 merge ctrld #892/#893, pc #1234/#1235 after infra fix
  4. Do not merge sa #261 without Gate 2 audit
- Cross-links: [Session report](tasks/pr-review-2026-06-13.md)

## Run — 2026-06-30

### Input tail

- Source report/snapshot: prior memory (2026-06-29 run) + live GitHub re-fetch
- PRs investigated: 48 in-scope open at start; cascade to 9 DIRTY during Phase 1
  merge burst

### Outcomes

| Repo                    | Old PR    | Disposition      | New PR | Notes                    |
| ----------------------- | --------- | ---------------- | ------ | ------------------------ |
| personal-config         | 1402      | SALVAGE          | 1433   | parse_inventory tests    |
| personal-config         | 1424      | SALVAGE          | 1434   | get_duplicates tests     |
| personal-config         | 1397      | SALVAGE          | 1435   | _find_matching_prs tests |
| personal-config         | 1393      | SALVAGE          | 1436   | create_denylist tests    |
| personal-config         | 1391      | SALVAGE          | 1437   | format_lists error paths |
| personal-config         | 1407      | SALVAGE          | 1438   | allowlist mocks          |
| personal-config         | 1369–1383 | CLOSE-SUPERSEDED | —      | stale session-doc drafts |
| email-security-pipeline | 1168      | SALVAGE          | 1192   | Palette fallback         |
| email-security-pipeline | 1175      | SALVAGE          | 1193   | NLP transformer tests    |
| email-security-pipeline | 1191      | SALVAGE          | 1194   | forgiving CLI selection  |

- Salvage draft PRs opened: 9
- Infra-fix draft PRs opened: 0
- Originals closed as superseded: 15
- Phase 1 merges (same session): 27

### Verification status

- Blocking checks: pc #1398 GitGuardian; pc #1422 CodeScene; esp #1179
  DIRTY+CodeScene
- CodeScene remediation commands posted: pc #1422, esp #1179

### Handoff

- Maintainer actions required:
  1. Review draft salvages pc #1433–#1438 and esp #1192–#1194
  2. Investigate pc #1398 GitGuardian before merge
  3. Re-run Phase 1 after CodeScene remediation on #1422
  4. Salvage or close esp #1179 after cs-agent cycle
- Cross-links: [Session report](tasks/pr-review-2026-06-30.md)

## Run — 2026-07-02

### Input tail

- Source report/snapshot: automation memory (2026-07-01 run) + live GitHub
  re-fetch
- PRs investigated: 5 in-scope open at start (2 DIRTY, 3 CLEAN)

### Outcomes

| Repo                              | Old PR | Disposition      | New PR | Notes                                |
| --------------------------------- | ------ | ---------------- | ------ | ------------------------------------ |
| series_correction_project_updated | 168    | MERGE            | —      | black formatting; all CI green       |
| personal-config                   | 1457   | CLOSE-SUPERSEDED | —      | session-doc draft                    |
| email-security-pipeline           | 1208   | CLOSE-NOOP       | —      | zero-diff Daily QA                   |
| email-security-pipeline           | 1202   | CLOSE-SUPERSEDED | —      | REDACTED_URL_PATTERN already on main |
| ctrld-sync                        | 965    | SALVAGE          | 970    | isatty guards only                   |

- Salvage draft PRs opened: 1 (#970)
- Infra-fix draft PRs opened: 0
- Phase 1 merges: 1 (sc#168)
- Originals closed: 4

### Verification status

- Blocking checks: none on `main`
- Local verify: `uv run pytest tests/test_ux.py -q` — 36 passed on cs salvage
  branch
- CodeScene remediation: cs#965 had prior `/cs-agent` posts; salvage diff is
  minimal

### Handoff

- Maintainer actions required: review draft cs#970 (T3 UX)
- Cross-links: [Session report](tasks/pr-review-2026-07-02.md)

## Run — 2026-07-03

### Input tail

- Source report/snapshot: `tasks/pr-review-2026-07-02.md` (prior remainder
  cs#970 merged) + live GitHub
- PRs investigated: 6 across 3 repos

### Salvage results

| Repo            | Old PR | Disposition   | New PR                                                          | Notes                                             |
| --------------- | ------ | ------------- | --------------------------------------------------------------- | ------------------------------------------------- |
| ctrld-sync      | #973   | SALVAGE draft | [#974](https://github.com/abhimehro/ctrld-sync/pull/974)        | Remaining isatty/newline cleanup after #970       |
| personal-config | #1466  | SALVAGE draft | [#1471](https://github.com/abhimehro/personal-config/pull/1471) | system_metrics.sh only; excluded get_repo_vars.sh |
| personal-config | #1470  | CLOSE         | —                                                               | Gitleaks + session.db artifacts                   |
| personal-config | #1468  | CLOSE         | —                                                               | Session doc superseded                            |

### Phase 1 merges (same session)

- esp [#1212](https://github.com/abhimehro/email-security-pipeline/pull/1212) —
  opencv pin
- pc [#1464](https://github.com/abhimehro/personal-config/pull/1464) — action
  SHA bumps

### Counts

- Deep-dived: 6
- Salvaged: 2
- Infra-fix PRs: 0 (pc#1464 merged directly)
- Closed superseded/no-op: 4
- Net new draft PRs awaiting human review: 2

### Verification status

- Local verify: `uv run pytest tests/test_ux.py -q` — 36 passed;
  `bash -n maintenance/bin/system_metrics.sh` — OK
- CodeScene remediation: `/cs-agent` posted on cs#973 before salvage close

### Handoff

- Maintainer actions required: review drafts pc#1471 (T3 perf) + cs#974 (T3 UX)
- Cross-links: [Session report](tasks/pr-review-2026-07-03.md)

## Run — 2026-07-05 (evening salvage)

### Input tail

- Source report/snapshot: morning Phase 1 via merged
  [#1504](https://github.com/abhimehro/personal-config/pull/1504) + live GitHub
  re-fetch
- PRs investigated: 9 across 5 repos (1 DIRTY, 2 new Palette, 2 deferred rpce, 1
  T1 salvage draft)

### Salvage results

| Repo                              | Old PR | Disposition   | New PR                                                                          | Notes                                                  |
| --------------------------------- | ------ | ------------- | ------------------------------------------------------------------------------- | ------------------------------------------------------ |
| series_correction_project_updated | #178   | SALVAGE draft | [#197](https://github.com/abhimehro/series_correction_project_updated/pull/197) | Gap-analysis helper extraction; excluded tasks/todo.md |
| ctrld-sync                        | #983   | SALVAGE draft | [#984](https://github.com/abhimehro/ctrld-sync/pull/984)                        | stderr cancel routing after #979/#981                  |

### Phase 1 merges (same evening pass)

- esp [#1229](https://github.com/abhimehro/email-security-pipeline/pull/1229) —
  zero-diff Daily QA
- pc [#1504](https://github.com/abhimehro/personal-config/pull/1504) — morning
  session artifacts

### Counts

- Deep-dived: 9
- Salvaged: 2
- Infra-fix PRs: 0
- Closed superseded: 2
- Phase 1 merges: 2
- Net new draft PRs awaiting human review: 2
- Deferred unchanged: 4 (pc#1505, sc#195, rpce#91, rpce#92)

### Verification status

- Local verify: `python3 -m pytest scripts/tests/ -q` — 58 passed (sc#197);
  `uv run pytest tests/test_ux.py -q` — 36 passed (cs#984)
- CodeScene remediation: `/cs-agent` posted on cs#983 and sc#178

### Handoff

- Maintainer actions required: T1 review sc#195; T3 review sc#197 + cs#984;
  merge pc#1505 when swift green; macOS format lane for rpce#91/#92
- Cross-links: [Session report](tasks/pr-review-2026-07-05.md)

## Run — 2026-07-15 (evening salvage)

### Input tail

- Source report: `tasks/pr-review-2026-07-15.md` Phase 1 remainder (9 PRs)
- PRs investigated: 9 across 6 repos (3 DIRTY conflict tails at start)

### Outcomes

| Repo              | Old PR                                                                                 | Disposition      | New PR                                                                                 | Notes                                     |
| ----------------- | -------------------------------------------------------------------------------------- | ---------------- | -------------------------------------------------------------------------------------- | ----------------------------------------- |
| personal-config   | [#1619](https://github.com/abhimehro/personal-config/pull/1619)                        | SALVAGE draft    | [#1623](https://github.com/abhimehro/personal-config/pull/1623)                        | Tuple `()` fallbacks; append-only bolt.md |
| Hydrograph        | [#364](https://github.com/abhimehro/Hydrograph_Versus_Seatek_Sensors_Project/pull/364) | SALVAGE draft    | [#366](https://github.com/abhimehro/Hydrograph_Versus_Seatek_Sensors_Project/pull/366) | `dict(series)` only; #363 already on main |
| series_correction | [#210](https://github.com/abhimehro/series_correction_project_updated/pull/210)        | CLOSE-SUPERSEDED | —                                                                                      | #224 (`53058c0`) already on main          |

- Originals closed as superseded: pc#1619, hg#364, sc#210
- Infra-fix draft PRs opened: 0
- Auto-resolved for Phase 1: esp#1264 (all required CI green)

### Verification status

- Blocking checks: none on `main`
- Local verify: `python3 -m py_compile` on pc salvage modules;
  `python3 -m pytest tests/test_validator.py -q` — 9 passed (hg#366)
- CodeScene remediation: not required on salvage diffs (routine T3 perf)

### Handoff

- Maintainer actions required: review draft salvages pc#1623 + hg#366; merge
  esp#1264 on next Phase 1; T1 escalations unchanged (cs#990, esp#1259, hg#357,
  rpce#112)
- Cross-links: [Session report](tasks/pr-review-2026-07-15.md)

## Run — 2026-07-16 (evening salvage)

### Input tail

- Source report: Phase 1 `tasks/pr-review-2026-07-16.md` via PR #1659 (23
  conflict defers)
- Live re-fetch: prior escalations mostly MERGED; 23+ conflicted bot PRs still
  open

### Outcomes

| Repo                    | Old PR                  | Disposition   | New PR                                                                                 | Notes                    |
| ----------------------- | ----------------------- | ------------- | -------------------------------------------------------------------------------------- | ------------------------ |
| personal-config         | #1627 #1645 #1656 #1649 | CLOSE         | —                                                                                      | superseded / no-op       |
| personal-config         | #1637 #1638 #1654       | SALVAGE draft | [#1661](https://github.com/abhimehro/personal-config/pull/1661)                        | adblock tests cluster    |
| personal-config         | #1642 #1646 #1647       | SALVAGE draft | [#1662](https://github.com/abhimehro/personal-config/pull/1662)                        | automation tests cluster |
| personal-config         | #1636                   | SALVAGE draft | [#1663](https://github.com/abhimehro/personal-config/pull/1663)                        | allowlist tests          |
| personal-config         | #1623                   | SALVAGE draft | [#1664](https://github.com/abhimehro/personal-config/pull/1664)                        | tuple fallbacks          |
| Seatek_Analysis         | #473                    | CLOSE         | —                                                                                      | superseded               |
| Seatek_Analysis         | #476                    | SALVAGE draft | [#478](https://github.com/abhimehro/Seatek_Analysis/pull/478)                          | rollmean3                |
| Seatek_Analysis         | #472                    | ESCALATE      | —                                                                                      | path hijack T1           |
| email-security-pipeline | #1276                   | CLOSE-NOOP    | —                                                                                      |                          |
| email-security-pipeline | #1279                   | SALVAGE draft | [#1287](https://github.com/abhimehro/email-security-pipeline/pull/1287)                |                          |
| email-security-pipeline | #1278                   | SALVAGE draft | [#1288](https://github.com/abhimehro/email-security-pipeline/pull/1288)                |                          |
| email-security-pipeline | #1284                   | SALVAGE draft | [#1289](https://github.com/abhimehro/email-security-pipeline/pull/1289)                |                          |
| email-security-pipeline | #1267                   | ESCALATE      | —                                                                                      | GitGuardian              |
| Hydrograph              | #376                    | SALVAGE draft | [#378](https://github.com/abhimehro/Hydrograph_Versus_Seatek_Sensors_Project/pull/378) | fixed dup staticmethod   |
| Hydrograph              | #373 #374               | AUTO-RESOLVED | —                                                                                      | Phase 1 candidates       |
| series_correction       | #235                    | SALVAGE draft | [#239](https://github.com/abhimehro/series_correction_project_updated/pull/239)        |                          |
| series_correction       | #238                    | SALVAGE draft | [#240](https://github.com/abhimehro/series_correction_project_updated/pull/240)        |                          |
| series_correction       | #233 #237               | ESCALATE      | —                                                                                      | auth                     |
| ctrld-sync              | #1018                   | DEFER         | —                                                                                      | CodeScene + SSRF delete  |
| personal-config         | #1629                   | ESCALATE      | —                                                                                      | Snyk hooks               |

- Salvage draft PRs opened: 11
- Infra-fix draft PRs opened: 0
- Closed superseded/no-op: 6
- Autonomous merges: 0

### Verification status

- Blocking checks on `main`: none identified
- Local verify: see `tasks/pr-review-2026-07-16.md` verification table
- CodeScene: `/cs-agent` already present on pc#1658 and cs#1018

### Handoff

- Maintainer: review T1 escalations first; then Phase 1 merge CLEAN
  deps/Palette; then T3 salvage drafts
- Cross-links: [Session report](tasks/pr-review-2026-07-16.md),
  [Triage](tasks/pr-triage.md)
- New lessons: 0dv (test clusters), 0dw (CodeScene + destructive security diffs)

## Run — 2026-07-17 (evening salvage)

### Input tail

- Source report: `tasks/pr-review-2026-07-17.md` Phase 1 remainder (via DIRTY
  [#1676](https://github.com/abhimehro/personal-config/pull/1676))
- Live re-fetch: 12 open in-scope PRs across 5 repos (ctrld-sync + Seatek at
  zero)

### Outcomes

| Repo            | Old PR                                                                                 | Disposition      | New PR                                                          | Notes                              |
| --------------- | -------------------------------------------------------------------------------------- | ---------------- | --------------------------------------------------------------- | ---------------------------------- |
| personal-config | [#1666](https://github.com/abhimehro/personal-config/pull/1666)                        | CLOSE-SUPERSEDED | —                                                               | already on main                    |
| personal-config | [#1663](https://github.com/abhimehro/personal-config/pull/1663)                        | SALVAGE draft    | [#1677](https://github.com/abhimehro/personal-config/pull/1677) | allowlist tests only               |
| personal-config | [#1668](https://github.com/abhimehro/personal-config/pull/1668)                        | SALVAGE draft    | [#1678](https://github.com/abhimehro/personal-config/pull/1678) | docs archive                       |
| personal-config | [#1669](https://github.com/abhimehro/personal-config/pull/1669)                        | SALVAGE draft    | [#1679](https://github.com/abhimehro/personal-config/pull/1679) | CI cache                           |
| Hydrograph      | [#381](https://github.com/abhimehro/Hydrograph_Versus_Seatek_Sensors_Project/pull/381) | CLOSE-SUPERSEDED | —                                                               | #378 helpers; CodeScene regression |
| personal-config | [#1665](https://github.com/abhimehro/personal-config/pull/1665)                        | CLOSE→session    | this session PR                                                 | folded 2026-07-16 report           |
| personal-config | [#1676](https://github.com/abhimehro/personal-config/pull/1676)                        | CLOSE→session    | this session PR                                                 | folded Phase 1 docs                |

- Salvage draft PRs opened: 3
- Infra-fix draft PRs opened: 0
- Closed superseded/no-op: 3 (+ 2 session-doc folds)
- Autonomous merges: 0
- Escalations unchanged: 5 (sc#233, esp#1267, pc#1670, hg#374, rpce#126/#127)

### Verification status

- Blocking checks on `main`: none identified
- Local verify:
  `pytest tests/test_extract_domains.py::TestProcessAllowlistFiles` — 3 passed;
  `bash tests/test_setup_shellcheck_action.sh` — 7 passed
- CodeScene remediation: hg#381 already had `/cs-agent`; closed as superseded
  instead of re-authoring inline form

### Handoff

- Maintainer: T1 sc#233 + esp#1267; T2 pc#1670 + hg#374 + rpce artifacts; T3
  drafts #1677/#1678/#1679
- Cross-links: [Session report](tasks/pr-review-2026-07-17.md),
  [Inventory](tasks/pr-inventory.md), [Triage](tasks/pr-triage.md)
- New lesson: 0dy (Bolt inlining undoes helper extraction)

## Run — 2026-07-19 (evening salvage)

### Input tail

- Source report: `tasks/pr-review-2026-07-19.md` Phase 1 remainder (via draft
  [#1695](https://github.com/abhimehro/personal-config/pull/1695))
- Live re-fetch: 7 open in-scope PRs (esp + Seatek at zero; new ctrld-sync #1030
  post-Phase-1)

### Outcomes

| Repo              | Old PR                                                                                                                    | Disposition      | New PR                                                     | Notes                                 |
| ----------------- | ------------------------------------------------------------------------------------------------------------------------- | ---------------- | ---------------------------------------------------------- | ------------------------------------- |
| ctrld-sync        | [#1030](https://github.com/abhimehro/ctrld-sync/pull/1030)                                                                | SALVAGE draft    | [#1031](https://github.com/abhimehro/ctrld-sync/pull/1031) | `_print_bold_header`; cs-agent posted |
| ctrld-sync        | [#1032](https://github.com/abhimehro/ctrld-sync/pull/1032)                                                                | CLOSE-SUPERSEDED | [#1031](https://github.com/abhimehro/ctrld-sync/pull/1031) | Jules re-open of same branch          |
| personal-config   | [#1670](https://github.com/abhimehro/personal-config/pull/1670)                                                           | ESCALATE         | —                                                          | 0ea shellcheck modify/delete          |
| series_correction | [#233](https://github.com/abhimehro/series_correction_project_updated/pull/233)                                           | ESCALATE         | —                                                          | auth                                  |
| Hydrograph        | [#374](https://github.com/abhimehro/Hydrograph_Versus_Seatek_Sensors_Project/pull/374)                                    | ESCALATE         | —                                                          | numpy major                           |
| repoprompt-ce     | [#126](https://github.com/abhimehro/repoprompt-ce/pull/126) / [#127](https://github.com/abhimehro/repoprompt-ce/pull/127) | ESCALATE         | —                                                          | 0dw tip artifacts                     |
| personal-config   | [#1695](https://github.com/abhimehro/personal-config/pull/1695)                                                           | CLOSE→session    | this session PR                                            | Phase 1 docs folded                   |

- Salvage draft PRs opened: 1
- Infra-fix draft PRs opened: 0
- Closed superseded/no-op: 2 (#1030/#1032) (+ 1 session-doc fold)
- Autonomous merges: 0
- Escalations left open: 5

### Verification status

- Blocking checks on `main`: none identified
- Local verify (ctrld-sync): py_compile + ruff + pytest 364 passed
- CodeScene: `/cs-agent` posted on #1030; remediation via helper extraction in
  #1031

### Handoff

- Maintainer: merge draft
  [#1031](https://github.com/abhimehro/ctrld-sync/pull/1031) after CI; then T1
  sc#233; T2 pc#1670 + hg#374 + rpce#126/#127
- Cross-links: [Session report](tasks/pr-review-2026-07-19.md),
  [Inventory](tasks/pr-inventory.md), [Triage](tasks/pr-triage.md)
- New lessons: 0ec (USE_COLORS helper isolation), 0ed (Jules re-open twin)

## Run — 2026-07-21 (evening salvage)

### Input tail

- Source report: `tasks/pr-review-2026-07-21.md` Phase 1 remainder (23 PRs)
- Live re-fetch: hg #374 MERGED; pc #1724 + esp #1320 auto-resolved CLEAN;
  conflict clusters salvaged

### Outcomes

| Repo                    | Old PR            | Disposition      | New PR                                                                  | Notes                                         |
| ----------------------- | ----------------- | ---------------- | ----------------------------------------------------------------------- | --------------------------------------------- |
| personal-config         | #1716 #1717 #1723 | SALVAGE draft    | [#1734](https://github.com/abhimehro/personal-config/pull/1734)         | automation tests cluster; no workflow smuggle |
| personal-config         | #1726             | SALVAGE draft    | [#1735](https://github.com/abhimehro/personal-config/pull/1735)         | shell-command tests + junk deletes            |
| personal-config         | #1718             | SALVAGE draft    | [#1736](https://github.com/abhimehro/personal-config/pull/1736)         | workflow_updater helpers                      |
| personal-config         | #1706             | CLOSE-SUPERSEDED | this session                                                            | prior Phase 2 docs                            |
| personal-config         | #1721             | ESCALATE         | —                                                                       | GH_TOKEN.env lru_cache                        |
| personal-config         | #1724             | AUTO-RESOLVED    | —                                                                       | next Phase 1                                  |
| email-security-pipeline | #1331             | SALVAGE draft    | [#1334](https://github.com/abhimehro/email-security-pipeline/pull/1334) | imap size list-comp; append bolt              |
| email-security-pipeline | #1314             | SALVAGE draft    | [#1335](https://github.com/abhimehro/email-security-pipeline/pull/1335) | extend+comprehension; append bolt             |
| email-security-pipeline | #1328 #1324 #1319 | ESCALATE         | —                                                                       | secrets/auth                                  |
| email-security-pipeline | #1327 #1330 #1311 | DEFER            | —                                                                       | CodeScene; cs-agent posted                    |
| email-security-pipeline | #1320             | AUTO-RESOLVED    | —                                                                       | next Phase 1                                  |
| Hydrograph              | #374              | DROP (MERGED)    | —                                                                       | numpy major landed                            |
| series_correction       | #275 #276 #268    | ESCALATE         | —                                                                       | auth dummy_todos (0ef)                        |
| repoprompt-ce           | #126 #127         | ESCALATE         | —                                                                       | tip artifact majors (0dw)                     |

- Salvage draft PRs opened: **5**
- Infra-fix draft PRs opened: **0**
- Closed superseded/no-op: **8**
- Autonomous merges: **0**
- Escalations left open: **10** (+ 3 CodeScene defers)

### Verification status

- Blocking checks on `main`: none identified
- Local verify: pc focused unit tests; esp 713 pytest passed on #1334 branch
- CodeScene: `/cs-agent` posted on esp #1330/#1311; already present on #1327

### Handoff

- Maintainer: merge drafts #1734/#1735/#1736 then esp #1334/#1335; Phase 1 for
  #1724/#1320; T1 auth/secrets escalations
- Cross-links: [Session report](tasks/pr-review-2026-07-21.md),
  [Inventory](tasks/pr-inventory.md), [Triage](tasks/pr-triage.md)
- New lesson: **0eh** (pr-visual-recap.yml smuggling in test PRs)

## Run — 2026-07-22

- Trigger: cron Phase 2 `0 17 * * *`
- Agent branch: `cursor-agent/automated-pr-salvage-6463`
- Preflight: PASS 7/7 (+ cursor-cloud-hooks)
- Source report: `tasks/pr-review-2026-07-22.md` Phase 1 remainder (17 PRs)
- Live re-fetch: conflict cascades on pc #1733, esp #1335/#1330; escalations
  unchanged

### Outcomes

| Repo                    | Old PR            | Disposition      | New PR                                                                  | Notes                                                         |
| ----------------------- | ----------------- | ---------------- | ----------------------------------------------------------------------- | ------------------------------------------------------------- |
| personal-config         | #1733             | SALVAGE draft    | [#1748](https://github.com/abhimehro/personal-config/pull/1748)         | recap-cli + token sanitize + MDX; lessons 0ei/0ej append-only |
| personal-config         | #1744             | ESCALATE         | —                                                                       | Actions SHA→floating tag                                      |
| personal-config         | #1721             | ESCALATE         | —                                                                       | GH_TOKEN/env cache + workflow noise                           |
| email-security-pipeline | #1335             | RE-SALVAGE draft | [#1341](https://github.com/abhimehro/email-security-pipeline/pull/1341) | extend+comprehension; closed prior salvage                    |
| email-security-pipeline | #1330             | SALVAGE adapted  | [#1342](https://github.com/abhimehro/email-security-pipeline/pull/1342) | IMAPClient config; kept FetchContext                          |
| email-security-pipeline | #1327             | DEFER            | —                                                                       | CodeScene fail; cs-agent already posted                       |
| email-security-pipeline | #1320             | DEFER            | —                                                                       | weakened test assertion                                       |
| email-security-pipeline | #1328 #1324 #1319 | ESCALATE         | —                                                                       | secrets/auth/token CLI                                        |
| series_correction       | #275 #276 #268    | ESCALATE         | —                                                                       | auth dummy_todos (0ef)                                        |
| Seatek_Analysis         | #507 #511         | ESCALATE         | —                                                                       | subprocess env / security refactor                            |
| repoprompt-ce           | #126 #127         | ESCALATE         | —                                                                       | tip artifact majors (0dw)                                     |
| ctrld-sync / Hydrograph | —                 | —                | —                                                                       | zero open                                                     |

- Salvage draft PRs opened: **3**
- Infra-fix draft PRs opened: **0**
- Closed superseded: **3**
- Autonomous merges: **0**
- Escalations left open: **11** (+ 2 defers)

### Verification status

- Local: `py_compile` on ESP salvages; `bash -n` + `node --check` on
  visual-recap scripts
- Blocking checks on `main`: none identified as whole-repo infra-broken
- CodeScene: no new `/cs-agent` (already present on #1327)

### Handoff

- Maintainer: merge drafts #1748 → #1341 → #1342; then T1 security escalations
- Cross-links: [Inventory](tasks/pr-inventory.md), [Triage](tasks/pr-triage.md),
  [Review](tasks/pr-review-2026-07-22.md)
- New lesson: **0ek** (re-salvage conflicted salvage drafts; adapt past sibling
  refactors)

## Run — 2026-07-23

- Trigger: cron Phase 2 `0 17 * * *`
- Agent branch: `cursor-agent/automated-pr-salvage-031d`
- Preflight: PASS 7/7 (+ cursor-cloud-hooks)
- Source report: `tasks/pr-review-2026-07-23.md` Phase 1 remainder (via draft
  [#1755](https://github.com/abhimehro/personal-config/pull/1755)) + live
  re-fetch
- Live extras: esp
  [#1345](https://github.com/abhimehro/email-security-pipeline/pull/1345) Jules
  blank-line QA (post–Phase 1)

### Outcomes

| Repo                    | Old PR                                                                                                                                                                                                                                                                                                                          | Disposition   | New PR                                                                  | Notes                                                 |
| ----------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ------------- | ----------------------------------------------------------------------- | ----------------------------------------------------- |
| email-security-pipeline | [#1327](https://github.com/abhimehro/email-security-pipeline/pull/1327)                                                                                                                                                                                                                                                         | SALVAGE draft | [#1346](https://github.com/abhimehro/email-security-pipeline/pull/1346) | SPF helper only; drop workflow churn; cs-agent posted |
| email-security-pipeline | [#1320](https://github.com/abhimehro/email-security-pipeline/pull/1320)                                                                                                                                                                                                                                                         | SALVAGE draft | [#1347](https://github.com/abhimehro/email-security-pipeline/pull/1347) | validate_subject_length + restored warning assert     |
| email-security-pipeline | [#1345](https://github.com/abhimehro/email-security-pipeline/pull/1345)                                                                                                                                                                                                                                                         | CLOSE no-op   | —                                                                       | single blank-line delete                              |
| personal-config         | [#1721](https://github.com/abhimehro/personal-config/pull/1721)                                                                                                                                                                                                                                                                 | ESCALATE      | —                                                                       | CONFLICTING + GH_TOKEN lru_cache                      |
| personal-config         | [#1744](https://github.com/abhimehro/personal-config/pull/1744)                                                                                                                                                                                                                                                                 | ESCALATE      | —                                                                       | Action SHA unpin (0z)                                 |
| personal-config         | [#1748](https://github.com/abhimehro/personal-config/pull/1748)/[#1749](https://github.com/abhimehro/personal-config/pull/1749)/[#1755](https://github.com/abhimehro/personal-config/pull/1755)                                                                                                                                 | DEFER human   | —                                                                       | prior draft salvages / Phase 1 docs                   |
| email-security-pipeline | [#1328](https://github.com/abhimehro/email-security-pipeline/pull/1328)/[#1324](https://github.com/abhimehro/email-security-pipeline/pull/1324)/[#1319](https://github.com/abhimehro/email-security-pipeline/pull/1319)                                                                                                         | ESCALATE      | —                                                                       | secrets/auth/token                                    |
| email-security-pipeline | [#1341](https://github.com/abhimehro/email-security-pipeline/pull/1341)/[#1342](https://github.com/abhimehro/email-security-pipeline/pull/1342)                                                                                                                                                                                 | DEFER human   | —                                                                       | prior Phase 2 drafts                                  |
| Seatek_Analysis         | [#518](https://github.com/abhimehro/Seatek_Analysis/pull/518)/[#507](https://github.com/abhimehro/Seatek_Analysis/pull/507)/[#511](https://github.com/abhimehro/Seatek_Analysis/pull/511)/[#514](https://github.com/abhimehro/Seatek_Analysis/pull/514)                                                                         | ESCALATE      | —                                                                       | env filter / path-IO / pandas major                   |
| series_correction       | [#285](https://github.com/abhimehro/series_correction_project_updated/pull/285)/[#276](https://github.com/abhimehro/series_correction_project_updated/pull/276)/[#275](https://github.com/abhimehro/series_correction_project_updated/pull/275)/[#268](https://github.com/abhimehro/series_correction_project_updated/pull/268) | ESCALATE      | —                                                                       | dummy_todos auth cluster (0ef)                        |
| repoprompt-ce           | [#126](https://github.com/abhimehro/repoprompt-ce/pull/126)/[#127](https://github.com/abhimehro/repoprompt-ce/pull/127)                                                                                                                                                                                                         | ESCALATE      | —                                                                       | tip artifact majors (0dw)                             |
| ctrld-sync / Hydrograph | —                                                                                                                                                                                                                                                                                                                               | —             | —                                                                       | zero open                                             |

- Salvage draft PRs opened: **2**
- Infra-fix draft PRs opened: **0**
- Closed superseded / no-op: **3** (#1327, #1320, #1345)
- Autonomous merges: **0**
- Escalations left open: **16** (+ prior human drafts deferred)

### Verification status

- Local: esp #1346 focused SPF/spam filter **13 passed**; #1347
  `TestHeaderSizeLimits` **7 passed**
- Blocking checks on `main`: none identified as whole-repo infra-broken
- CodeScene: `/cs-agent` posted on salvage
  [#1346](https://github.com/abhimehro/email-security-pipeline/pull/1346);
  already present on sc #285

### Handoff

1. Merge drafts: esp
   [#1346](https://github.com/abhimehro/email-security-pipeline/pull/1346) →
   [#1347](https://github.com/abhimehro/email-security-pipeline/pull/1347); then
   prior
   [#1341](https://github.com/abhimehro/email-security-pipeline/pull/1341)/[#1342](https://github.com/abhimehro/email-security-pipeline/pull/1342);
   pc [#1748](https://github.com/abhimehro/personal-config/pull/1748)
2. T1 human: esp #1328/#1324/#1319; sc #275/#276/#268/#285; Seatek
   #518/#507/#511
3. T2 human: pc #1721/#1744; Seatek #514; rpce #126/#127
4. Fold/close stale docs drafts #1749/#1755 after this session PR lands

- Cross-links: [Inventory](tasks/pr-inventory.md), [Triage](tasks/pr-triage.md),
  [Review](tasks/pr-review-2026-07-23.md)
- New lessons: **0ek** (backfill re-salvage), **0el** (Sentinel siblings),
  **0em** (Dependabot title), **0en** (restore warning assert)

## Run — 2026-07-25

- Trigger: cron Phase 2 `0 17 * * *`
- Agent branch: `cursor-agent/automated-pr-salvage-a2fb`
- Preflight: PASS 7/7 (+ cursor-cloud-hooks)
- Source report: `tasks/pr-review-2026-07-25.md` Phase 1 remainder (via draft
  [#1771](https://github.com/abhimehro/personal-config/pull/1771)) + live
  re-fetch

### Outcomes

| Repo                    | Old PR                                                                                                                                                                                                                                                                                                                                                                  | Disposition           | New PR / Branch                                                | Notes                                                                            |
| ----------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | --------------------- | -------------------------------------------------------------- | -------------------------------------------------------------------------------- |
| personal-config         | [#1748](https://github.com/abhimehro/personal-config/pull/1748)                                                                                                                                                                                                                                                                                                         | SALVAGE branch pushed | `cursor-agent/salvage-pc-1748-visual-recap-v2-a2fb` @ a2208a73 | Journal-only conflict; Lesson 0ei append; MDX 9/9; draft PR create blocked (0eq) |
| personal-config         | [#1721](https://github.com/abhimehro/personal-config/pull/1721)                                                                                                                                                                                                                                                                                                         | ESCALATE              | —                                                              | lru_cache on GH_TOKEN env loader                                                 |
| personal-config         | [#1766](https://github.com/abhimehro/personal-config/pull/1766)/[#1767](https://github.com/abhimehro/personal-config/pull/1767)/[#1769](https://github.com/abhimehro/personal-config/pull/1769)                                                                                                                                                                         | ESCALATE              | —                                                              | SSRF / token helpers (1766 now CLEAN)                                            |
| ctrld-sync              | [#1060](https://github.com/abhimehro/ctrld-sync/pull/1060)                                                                                                                                                                                                                                                                                                              | ESCALATE              | —                                                              | Sentinel exception chaining                                                      |
| email-security-pipeline | [#1360](https://github.com/abhimehro/email-security-pipeline/pull/1360)                                                                                                                                                                                                                                                                                                 | CLOSE-CANDIDATE no-op | —                                                              | zero-diff Jules QA; close blocked                                                |
| email-security-pipeline | [#1353](https://github.com/abhimehro/email-security-pipeline/pull/1353)/[#1328](https://github.com/abhimehro/email-security-pipeline/pull/1328)/[#1324](https://github.com/abhimehro/email-security-pipeline/pull/1324)/[#1359](https://github.com/abhimehro/email-security-pipeline/pull/1359)/[#1319](https://github.com/abhimehro/email-security-pipeline/pull/1319) | ESCALATE              | —                                                              | TOCTOU / Auth-Results / gh_token_cli                                             |
| email-security-pipeline | [#1342](https://github.com/abhimehro/email-security-pipeline/pull/1342)                                                                                                                                                                                                                                                                                                 | DEFER human           | —                                                              | prior salvage draft CLEAN                                                        |
| Seatek_Analysis         | [#525](https://github.com/abhimehro/Seatek_Analysis/pull/525)/[#518](https://github.com/abhimehro/Seatek_Analysis/pull/518)/[#507](https://github.com/abhimehro/Seatek_Analysis/pull/507)/[#521](https://github.com/abhimehro/Seatek_Analysis/pull/521)/[#511](https://github.com/abhimehro/Seatek_Analysis/pull/511)                                                   | ESCALATE              | —                                                              | Sentinel siblings / pandas / Devin                                               |
| Hydrograph…             | [#413](https://github.com/abhimehro/Hydrograph_Versus_Seatek_Sensors_Project/pull/413)                                                                                                                                                                                                                                                                                  | ESCALATE              | —                                                              | Sentinel DoS + CodeScene; cs-agent already posted                                |
| series_correction…      | [#285](https://github.com/abhimehro/series_correction_project_updated/pull/285)/[#276](https://github.com/abhimehro/series_correction_project_updated/pull/276)/[#275](https://github.com/abhimehro/series_correction_project_updated/pull/275)/[#268](https://github.com/abhimehro/series_correction_project_updated/pull/268)                                         | ESCALATE              | —                                                              | dummy_todos 0ef                                                                  |
| repoprompt-ce           | [#126](https://github.com/abhimehro/repoprompt-ce/pull/126)/[#127](https://github.com/abhimehro/repoprompt-ce/pull/127)                                                                                                                                                                                                                                                 | ESCALATE              | —                                                              | tip artifact majors CONFLICTING 0dw                                              |

- Salvage draft PRs opened via API: **0** (permission)
- Salvage branches pushed: **1**
- Infra-fix draft PRs opened: **0**
- Closed superseded / no-op via API: **0**
- Autonomous merges: **0**
- Escalations left open: **23** (+ 1 close-candidate)

### Verification status

- Local: `bash tests/test_fix_recap_mdx_diff_strings.sh` → 9 passed;
  `node --check` on MDX helpers
- Blocking checks on `main`: none identified as whole-repo infra-broken
- CodeScene: `/cs-agent` already present on hg #413 and sc #285; no new posts
  needed

### Handoff

1. **Open draft** from
   https://github.com/abhimehro/personal-config/compare/main...cursor-agent/salvage-pc-1748-visual-recap-v2-a2fb?quick_pull=1
   then close #1748 as superseded
2. Close esp
   [#1360](https://github.com/abhimehro/email-security-pipeline/pull/1360)
   (zero-diff)
3. Merge prior drafts when ready: esp
   [#1342](https://github.com/abhimehro/email-security-pipeline/pull/1342); pc
   visual-recap draft after step 1
4. T1 human: pc #1766/#1767/#1769; esp TOCTOU/Auth; Seatek Sentinel siblings; sc
   dummy_todos; hg #413
5. T2 human: pc #1721; rpce #126/#127; Seatek #521
6. Rotate expired `GH_TOKEN` PAT (Phase 1 Lesson 0eo) so future sessions can
   `gh pr create/close/comment`

- Cross-links: [Inventory](tasks/pr-inventory.md), [Triage](tasks/pr-triage.md),
  [Review](tasks/pr-review-2026-07-25.md)
- New lesson: **0eq** (Cursor app token push-ok / PR-write blocked for salvage
  branches)

## Run — 2026-07-31

- Trigger: cron Phase 2 `0 17 * * *`
- Agent branch: `cursor-agent/automated-pr-salvage-workflow-e012`
- Preflight: PASS 7/7 (+ cursor-cloud-hooks)
- Source: Phase 1
  [#1855](https://github.com/abhimehro/personal-config/pull/1855) remainder +
  live CONFLICTING re-fetch
- Auth: `abhimehro` PAT (Lesson 0ew) — create/close OK

### Outcomes

| Repo                    | Old PR               | Disposition           | New PR                                                          | Notes                                |
| ----------------------- | -------------------- | --------------------- | --------------------------------------------------------------- | ------------------------------------ |
| personal-config         | #1840/#1835          | SALVAGE               | [#1856](https://github.com/abhimehro/personal-config/pull/1856) | skip-link; journal 0y                |
| personal-config         | #1824/#1823          | SALVAGE               | [#1857](https://github.com/abhimehro/personal-config/pull/1857) | combined 0ey                         |
| personal-config         | #1830                | CLOSE-SUPERSEDED      | —                                                               | regex in #1854; harmful extras       |
| personal-config         | #1822/#1841          | ESCALATE              | —                                                               | CORS / auth env                      |
| personal-config         | #1825                | REQUEST_CHANGES       | —                                                               | scratch                              |
| Seatek_Analysis         | #552                 | SALVAGE               | [#571](https://github.com/abhimehro/Seatek_Analysis/pull/571)   | T1 list-only shell                   |
| Seatek_Analysis         | #554                 | DEFER                 | —                                                               | warn_on_* redesign                   |
| Seatek_Analysis         | #560                 | REQUEST_CHANGES       | —                                                               | workflow scope                       |
| Hydrograph…             | #443/#442            | AUTO-RESOLVED         | —                                                               | CLEAN after #440                     |
| Hydrograph…             | #445                 | ESCALATE              | —                                                               | path traversal                       |
| series…                 | #336                 | ESCALATE              | —                                                               | broken authenticate + CHANGELOG wipe |
| series…                 | #322                 | ESCALATE/DEFER        | —                                                               | auth-adjacent                        |
| series…                 | #337                 | REQUEST_CHANGES       | —                                                               | NaN masking                          |
| ctrld-sync              | #1086/#1088/#1081    | REQUEST_CHANGES/DEFER | —                                                               | junk / CodeScene / CI                |
| email-security-pipeline | #1394                | DEFER                 | —                                                               | S6                                   |
| repoprompt-ce           | #147/#158 + CI queue | ESCALATE/DEFER        | —                                                               | no salvage                           |

- Salvage draft PRs opened: **3**
- Closed superseded / no-op: **6**
- Autonomous merges: **0**
- Infra-fix drafts: **0**

### Handoff

1. **Human merge drafts (priority):** seatek
   [#571](https://github.com/abhimehro/Seatek_Analysis/pull/571) (T1) → pc
   [#1856](https://github.com/abhimehro/personal-config/pull/1856)/[#1857](https://github.com/abhimehro/personal-config/pull/1857)
2. **T1 human:** pc #1822/#1841; seatek #568/#555; hg #445; series #336; rpce
   #158/#147
3. Next Phase 1: hg #443/#442 now CLEAN
4. Skip `request_reviewers` when author is abhimehro (0ew)

- Cross-links: [Inventory](tasks/pr-inventory.md), [Triage](tasks/pr-triage.md),
  [Review](tasks/pr-review-2026-07-31.md)
- New lesson: **0fa** (detect mid-function corruption in auth salvages)

## Run — 2026-08-02

- Trigger: cron Phase 2 `0 17 * * *`
- Agent branch: `cursor-agent/automated-pr-salvage-workflow-d8a4`
- Preflight: PASS 7/7 (+ cursor-cloud-hooks)
- Source: Phase 1
  [#1884](https://github.com/abhimehro/personal-config/pull/1884) /
  `pr-review-2026-08-02.md` remainder + live CONFLICTING re-fetch
- Auth: `abhimehro` PAT (Lesson 0ew) — create/close OK

### Outcomes

| Repo                 | Old PR                        | Disposition      | New PR                                                      | Notes                                                |
| -------------------- | ----------------------------- | ---------------- | ----------------------------------------------------------- | ---------------------------------------------------- |
| Hydrograph…          | #445/#448/#450                | CLOSE-SUPERSEDED | —                                                           | `is_safe_path` already on main; #448 duplicate bloat |
| repoprompt-ce        | #165/#158                     | SALVAGE          | [#171](https://github.com/abhimehro/repoprompt-ce/pull/171) | TOCTOU-only; strip ToolOutputFormatter churn         |
| repoprompt-ce        | #158                          | CLOSE-SUPERSEDED | #171                                                        | DIRTY twin                                           |
| personal-config      | #1841                         | ESCALATE         | —                                                           | CLEAN Sentinel                                       |
| Seatek_Analysis      | #580/#573                     | ESCALATE         | —                                                           | CLEAN Sentinel                                       |
| repoprompt-ce        | #144/#147/#148/#152/#157/#161 | DEFER            | —                                                           | large drift pile                                     |
| ctrld / esp / series | —                             | EMPTY            | —                                                           | prior salvages merged on Phase 1                     |

- Salvage draft PRs opened: **1**
- Closed superseded / no-op: **4**
- Autonomous merges: **0**
- Infra-fix drafts: **0**

### Handoff

1. **Human merge draft:**
   [rpce #171](https://github.com/abhimehro/repoprompt-ce/pull/171) (TOCTOU) —
   then close #165
2. **T1 human security:** pc #1841; seatek #580/#573
3. **Phase 1 follow-up:** rpce UNSTABLE a11y/Bolt queue
   (#163/#164/#168/#169/#170)
4. Skip `request_reviewers` when author is abhimehro (0ew)

- Cross-links: [Inventory](tasks/pr-inventory.md), [Triage](tasks/pr-triage.md),
  [Review](tasks/pr-review-2026-08-02.md)
- New lesson: **0fd** (close Sentinel clusters when main already has the guard)

## Run — 2026-08-12

- Trigger: cron Phase 2 `0 17 * * *`
- Agent branch: `cursor-agent/automated-pr-salvage-workflow-2869`
- Preflight: PASS (+ cursor-cloud-hooks)
- Source: Phase 1 [#1977](https://github.com/abhimehro/personal-config/pull/1977) / `pr-review-2026-08-12.md` remainder + live CONFLICTING re-fetch
- Auth: `abhimehro` PAT (Lesson 0ew) — create/close OK

### Outcomes

| Repo | Old PR | Disposition | New PR | Notes |
|------|--------|-------------|--------|-------|
| Hydrograph… | #504 | SALVAGE | [#507](https://github.com/abhimehro/Hydrograph_Versus_Seatek_Sensors_Project/pull/507) | newline/CR tests + journal; regex already on main |
| ctrld-sync | #1150 | SALVAGE | [#1159](https://github.com/abhimehro/ctrld-sync/pull/1159) | pluralize dry-run; strip lock/deps (0fm) |
| repoprompt-ce | #224 | SALVAGE | [#237](https://github.com/abhimehro/repoprompt-ce/pull/237) | REPLInputParserTests only (0fj) |
| series… | #378 | CLOSE no-op | — | `dummy_todos.py` absent on main |
| repoprompt-ce | #231 | HOLD/ESCALATE | — | DateFormatter + contamination |
| personal-config | #1977 | DOCS recover | this docs PR | Phase 1 08-08…12 + Lessons 0fl/0fm |

- Salvage draft PRs opened: **3**
- Closed superseded / no-op: **4**
- Autonomous merges: **0**
- Infra-fix drafts: **0**

### Handoff

1. **Human merge drafts:** Hydro [#507](https://github.com/abhimehro/Hydrograph_Versus_Seatek_Sensors_Project/pull/507) → ctrld [#1159](https://github.com/abhimehro/ctrld-sync/pull/1159) → rpce [#237](https://github.com/abhimehro/repoprompt-ce/pull/237)
2. **T1 human:** pc#1907 CORS; ctrld#1156 TOCTOU / #1136 mypy; esp#1444 opencv; Seatek#657; series#386/#385; rpce#232/#228/#231
3. Skip `request_reviewers` when author is abhimehro (0ew)
4. New lesson: **0fq** (close auth salvages when demo module deleted from main)

- Cross-links: [Inventory](tasks/pr-inventory.md), [Triage](tasks/pr-triage.md), [Review](tasks/pr-review-2026-08-12.md)
