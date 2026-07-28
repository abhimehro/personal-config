# Phase 2 Salvage Todo — 2026-07-28

- [x] Preflight (gh auth, 7 repos, cursor-cloud-hooks)
- [x] Live re-fetch Phase 1 remainder + CONFLICTING
- [x] Salvage pc #1800 → draft #1804
- [x] Salvage pc #1791 → draft #1803
- [x] Salvage cs #1064 → draft #1072 (364 tests)
- [x] MCP CLOSE-SUPERSEDED / REQUEST_CHANGES / ESCALATE reviews
- [x] Request reviewers on salvage drafts
- [x] Write pr-inventory.md, pr-triage.md, Phase 2 addendum, lessons 0et
- [x] Commit/push session docs + open_git_pr for docs branch
- [x] Notion audit page + automation memory update
# Session plan — ABHI-1517: Pin GitHub Actions & Tighten Permissions

- [x] Audit all 17 active workflow files for unpinned actions, over-broad `permissions`, `pull_request_target`, PAT/App-token exposure, implicit `github.token`, and attacker-controlled interpolation
- [x] Independently re-resolve every floating tag to a verified 40-character commit SHA
- [x] Pin all remote `uses:` references to full SHAs and clean mismatched/duplicate version comments
- [x] Apply least-privilege, job-level `permissions` and top-level defaults where needed
- [x] Audit `persist-credentials` on checkout steps; set `false` unless the job pushes
- [x] Add fail-closed `.github/scripts/validate_workflow_pins.py` gate and wire it into CI
- [x] Validate with YAML parsing, `actionlint`, `pinact --no-fix`, `make test-quick`/`make test`/`make test-python`, and targeted `trunk check`
- [x] Resolve CI / CodeScene code-health failures on `validate_workflow_pins.py`
- [x] Open PR with ELIR handoff and post-merge repository default `GITHUB_TOKEN` guidance
- [x] Update Linear ABHI-1517 with implementation summary and status
# Phase 2 Salvage — 2026-07-27

## Preflight
- [x] `unset GH_TOKEN` (Lesson 0eo); hosts.yml Cursor token active
- [x] `make cursor-cloud-hooks`
- [x] `./scripts/preflight-gh-pr-automation.sh` PASS 7/7
- [x] Read Phase 1 remainder `tasks/pr-review-2026-07-26.md`
- [x] Live re-fetch open PRs across 7 repos

## Inventory / triage
- [x] Write `tasks/pr-inventory.md`
- [x] Write `tasks/pr-triage.md`
- [x] Deep-dive CONFLICTING: esp#1362, hg#413
- [x] Classify Phase 1 escalated tail (cs#1060, esp#1366, Seatek cluster, #521)

## Salvage actions (never autonomous merge)
- [x] esp#1362: CLOSE-SUPERSEDED (MCP review) — prefer #1370 + main #1353
- [x] hg#413: CLOSE-SUPERSEDED (MCP review) — prefer #418
- [x] esp#1366: REQUEST_CHANGES (0er)
- [x] Seatek #507/#518/#525: ESCALATE (0ej)
- [x] cs#1060: ESCALATE T1
- [x] CodeScene: `/cs-agent` via MCP on ctrld#1066
- [x] MCP reviews on preferred twins #1370/#418
- [ ] Human must close #1362/#413 (API close blocked 0eq)
- [ ] request_reviewers blocked (author=abhimehro)

## Deliverables
- [x] `tasks/pr-inventory.md`
- [x] `tasks/pr-triage.md`
- [x] `tasks/pr-review-2026-07-27.md`
- [x] Append `tasks/salvage-session-reports.md`
- [x] Lesson 0es in `tasks/lessons.md`
- [x] Commit+push session docs on `cursor-agent/automated-pr-salvage-workflow-3074`
- [x] `open_git_pr` → https://github.com/abhimehro/personal-config/pull/1793
- [x] Memory + Notion audit trail
# Session plan — 2026-07-28 (Phase 1 cron) — complete

- [x] Preflight gate PASS 7/7
- [x] Inventory all open automation PRs → `tasks/pr-inventory.md`
- [x] Triage → `tasks/pr-triage.md`
- [x] Merge zero-diff Daily QA (squash)
- [x] Merge green Dependabot patch bumps
- [x] Review/merge safe Bolt/Palette/routine
- [x] Escalate Sentinel/security; REQUEST_CHANGES on 0er/#1792/#535
- [x] Defer draft Phase-2 / CONFLICTING bolt.md siblings
- [x] Post MCP reviews (close API unavailable — 0es)
- [x] Write `pr-review-2026-07-28.md`, update lessons + review-session-reports
- [x] Commit/push docs on `cursor-agent/automated-pr-workflow-3d54` + open PR (#1802)
# ABHI-1549 — Standardize placeholder secrets in templates

**Route:** T2+S+H  
**Trust boundary:** Committed templates must never hold live secrets; only `op://` refs or unmistakably fake `REPLACE_WITH_*` markers.

## Plan

- [x] Audit flagged files + all `*.template` / `*.example`
- [x] Sync legacy `mcp-configs/mcp-servers.template` to `op://` (match canonical `.json`)
- [x] Rewrite `docs/MCP_SECRETS_MANAGEMENT.md` — clear placeholders + prefer `op://`
- [x] Standardize `.env.example` (and related examples) to `REPLACE_WITH_*`
- [x] Document that Windsurf `op://` templates are secure refs, not secrets
- [x] Extend `tests/test_repo_credential_hygiene.sh` for ABHI-1549 regressions
- [x] Verify with grep / quick tests; commit + PR; comment on Linear

## Security considerations

- `op://Personal/...` is intentional 1Password injection syntax — keep it.
- Ambiguous strings like `your_actual_*_here` are the real problem (looks like a filled value).
- Do not weaken generators that inject secrets outside the repo.
