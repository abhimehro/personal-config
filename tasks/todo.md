# Exclusive docs lineage 0hk (2026-09-18, this Stage 1 session)

T5 — Stage 2/3 must not think heal-forward is still Trunk-queued, and must
not disable Stage 1 to “hand off” to Stage 2.

- [x] Confirm live GetAutomation: Stage 1/2/3 completion on, calibration off
- [x] Rewrite Downstream unblock: #2224/#2225/#2226 on `main`
- [x] Lesson **0hk**: keep Stage 1 enabled; ignore 2026-09-16 disabled table
- [x] Checklist enablement column matches live GetAutomation (lineage only)
- [x] Contract tests for 0hk without changing 147/21/17 metrics
- [ ] Push `pr-lifecycle-docs-20260918`; do **not** `/trunk merge` #2222
- [ ] HITL paste still unproved until `HITL_PASTE_DONE`

# Heal-forward cascade (2026-09-18)

T2 — Stage 2/3 heal leftover Stage 1 work instead of hard-stopping.

- [x] `HEAL_THEN_PROCEED` replaces `FEED_FAIL` / `UPSTREAM_PAUSE` stop actions
- [x] Stage 1/2/3 prompts + lifecycle contract + dashboard checklist
- [x] Shared-ownership / security-first development-partner language
      (Copilot profile, `AGENTS.md`, `REVIEW.md`) in all three prompts
- [x] Partner profile apply-not-cite bindings (Copilot + `AGENTS.md` +
      `REVIEW.md` + `.cursorrules`) in prompts, contract, and tests
- [x] Tests + export `--write`
- [x] Product PR #2224; subscribed GitHub PR + CI
- [ ] HITL: paste updated prompts into UUID automations (keep Stage 1/2/3
      completion enabled; do not disable Stage 1)
- [x] Land #2224 (on `main` as `0cf4928e`; do not tell Stage 2 it is queued)

## CAS/export decoupling (2026-09-18)

T3+S — Wrap-only Cursor export drift must not halt the daily drain.

- [x] Decouple ledger CAS `validate()` from export/prompt byte-equality
- [x] `sync_cursor_export_prompts.py --write` so CI `--check` is green
- [x] Stage 1/2/3 prompts: repair wrap-only; ANALYSIS_ERROR is ledger-only
- [x] Stage 2/3 fail-closed after ledger preflight, no ANALYSIS_ERROR theater
- [x] Tests + `make test-quick` includes `--check`
- [x] Product PR #2223; subscribed GitHub PR + CI
- [x] Qodo: wrap 79-char patch line; merge CI `--include-exports` + paths
- [x] Codacy: one-line docstrings (D212 vs D213 ping-pong on the same pair)
- [x] Land #2223 (export-authority CI + pinact 4.1.1; Trunk queue, no self-approve)

## Stage 1→2 fail-closed cascade (2026-09-16)

T1+S — Prompt/spec fail-closed cascade + Dashboard ID align + sample verify.

- [x] venv + health monitor baseline on fetched ledger
- [x] Stage 1/2/3 prompts: feed fingerprint + FEED_FAIL short-circuit
- [x] `docs/automated-pr-lifecycle.md` cascade paragraph
- [x] Dashboard checklist: live UUID enablement + fetch-before-health
- [x] `.venv/` gitignore; sync Cursor export prompts
- [x] Sample WI emission/claim via `pr_lifecycle_feed_cascade_verify.py` + tests
- [x] Health verify: tip `starvation=false` (eligible drained); inject proves
      CLAIM
- [x] CI: CodeScene Excess Args + Codacy ≤0 new issues on cascade/verify
- [ ] HITL: paste updated prompts into UUID automations; sample live Stage 1 CAS

## PR #2175 stack resolution — 2026-09-09

T3+S — Address review comments and failing checks. Do not bump
`policy_revision`. Salvage cap stays 10 (EMPTY_INTAKE was unread ledger).

- [x] Inventory PR comments + failing CodeScene/Codacy checks
- [x] Always sanitize ledger file before validate+upload
- [x] CAS: no stale-content retry; split helpers for CodeScene
- [x] `--out` path containment; sanitized GitHub errors
- [x] Prompts: `--message`; CLI default message
- [x] Revise #2176: drop salvage-5 revert; closed empty stacked follow-up
- [x] Fold #2179 assertion onto #2177 (`7cc5c0e2`); close #2179
- [x] Batch #2172/#2180 EOF-append + Codacy URL wraps
- [x] CodeScene: split blob decode + flatten stale-CAS test; HTTPS-only opener
- [x] Hybrid sanitize (line-strip + leftover dump); extract GitHub HTTP client
- [x] Split Git Data helpers + clear Codacy notices (NLOC/D213/RUF022/S310)
- [x] Codacy follow-up: D212 one-liners, drop unused noqa, isort aliases, MD025
- [x] Codacy CPD: reassemble GitHub Request without safe_urlopen clone
- [x] Codacy unused-attribute: pass Request data/method in the constructor
- [ ] `gh stack` sync product/docs/copilot layers; do not merge

## Three-stage scheduled Cursor reliability (2026-09-08)

T3+S — Diagnose then repair at the cause. Do not bump `policy_revision`.
Calibration stays APPROVED 7/7. Do not reset to REPORT_ONLY.

- [x] Diagnose: Devin vs scheduled Cursor (schema extra keys + >1MB Contents
      GET)
- [x] Load-time strip of `latest_transition` / `latest_transition_kind` only
- [x] Persist helper so writers cannot dump in-memory projection fields
- [x] Git Data API CAS + ref restore (Contents GET encoding=none above 1MB)
- [x] Tests: schema still rejects extra keys; validate() sanitizes known pair
- [x] Reassess salvage-5: raise Stage 2 to 10 and Stage 3 completions to 15
- [x] CAS-repair runtime ledger rev 67→68 (strip only; no item transitions)
- [x] Prove: validator PASS + health CLI + bounded green BOT drain
- [x] Commit, push designated branch, open product PR

## PR backlog burndown + Stage 2 starvation (2026-08-30)

T5 — Orchestrate. 20 mutations/day equals arrivals; Stage 2 is idle. Do not bump
`policy_revision`. Stage 2 still never merges. PR Desk stays read-only.

- [x] Diagnose: cap-equals-arrivals, Stage 2 WI starvation, Stage 3 bounce
      wasting overflow completions
- [x] Stage 1 caps 80/40; salvage-eligible reselect; WI queue is bookkeeping
- [x] Stage 2 EMPTY_INTAKE_STARVATION label; still no invented recoveries
- [x] Stage 3 complete MERGEABLE overflow; mechanical HOLD_CONTRACT → WI
- [x] Monitor `scripts/pr_lifecycle_pipeline_health.py`; PR Desk health line
- [x] Owned-without-WI does not hide starvation; WI completeness from schema
- [x] Tests + `sync_cursor_export_prompts.py --write/--check`
- [x] Commit, push, open PR (not Trunk-merged unless asked)
- [ ] HITL: paste Stage 1/2/3 completion prompts; keep calibration disabled

## Grok Bot PR Desk (filter, not a fourth stage) — 2026-08-27

Paste-ready files: `docs/grok-bot/`. Do not give this Bot merge/issue/CAS
authority. Dashboard Automations stay the only PR actors.

- [ ] Create Bot **PR Desk**; paste `docs/grok-bot/pr-desk.profile.md`
- [ ] Connect GitHub (read) + Notion plugins only
- [ ] Run `docs/grok-bot/pr-desk.first-task.md`; correct once
- [ ] Save skill + weekday 8:00 PM CDT routine from
      `docs/grok-bot/pr-desk.skill-digest.md` after the format is good
- [ ] Do not add a GitHub-notification listener in v1

## PR pipeline throughput + Stage 3 approval (2026-08-26)

T5 — Orchestrate. Drain the ~200-PR backlog. Do not bump `policy_revision`.
Stage 2 still never merges.

- [x] Diagnose: SHA_MATCH skip, HOLD_CANONICAL parking, HOLD_PLATFORM on
      GitHub-green BOT, Stage 3 REPORT_ONLY parking lot, empty Stage 2
- [x] Stage 1: SHA_MATCH reselect, canonical-pick, salvage-only HOLD_PLATFORM,
      `.jules/` journal not sticky, product-mutation budget, throughput FAIL
- [x] Stage 2: empty-intake stop
- [x] Stage 3: bounce executable clusters to Stage 1; packets only for
      irreducible sticky/HUMAN/real platform
- [x] Human APPROVE Stage 3 (7/7 successful CALIBRATION events; user 2026-08-26)
      in runtime ledger via Contents API CAS (rev 22→23, commit
      `2f024d1f659fa8d8cd5b8bf76d40d90da3505b23`); Dashboard: disable
      calibration, enable completion, paste prompts
- [x] Tests + `sync_cursor_export_prompts.py --write/--check`
- [x] Commit, push, open PR (not Trunk-merged unless asked)

## Phase 1 PR Review — 2026-08-17

Branch: `cursor-agent/automated-pr-workflow-2dfb` Mode: review-and-merge. Stale:
30 days. Auto-fix: safe routine only. Merge: squash.

- [x] Preflight gate (`preflight-gh-pr-automation.sh`, 7/7)
- [x] `make cursor-cloud-hooks`
- [x] Live-fetch open auto PRs (do not trust 2026-08-16 snapshot)
- [x] Classify + write `tasks/pr-inventory.md` / `tasks/pr-triage.md`
- [x] Gate 1–4 on MERGE candidates; re-check 0fs after any lock merge
- [x] Adversarial multi-model review on representative diffs
- [x] APPROVE + squash-merge green routine PRs (6)
- [x] REQUEST_CHANGES / ESCALATE security, majors, trust-boundary, failing CI
- [x] Close duplicates / zero-diff / superseded (4)
- [x] CodeScene trigger skipped (MCP down; pc#1980 already triggered 08-16)
- [x] Append `tasks/review-session-reports.md` + dated snapshot + lesson 0ft
- [x] `make test-quick` + `make lint-errors` on docs branch
- [x] Commit/push docs; open artifacts PR
- [x] Update automation memory + Notion

## Phase 2 remainder (drafts only — do not merge)

- Sentinel/CORS/TOCTOU/CWE clusters stay ESCALATE
- Majors with red CI stay ESCALATE
- 0fo/0fp/0fg/0fs/0ft HOLD until re-verified vs current main
- DIRTY ctrld#1188 uv-only → draft salvage
- Do not merge salvage drafts or auth/payment/schema PRs

## Stage 2 salvage 2026-08-20

- [x] Fetch/validate runtime ledger (`github_contents_api`, rev 5,
      PR_LIFECYCLE_VALID)
- [x] Read last Stage 2 records, lessons, Stage-2-owned items
- [x] Preflight 7/7
- [x] Live-reconcile six STAGE2_QUEUED work items (cap 5; leave ctrld #1161
      queued)
- [x] Recover five work items: drafts hydro #543, Seatek #708; structured fails
      #673/#247/#271
- [x] ACK Stage 1 handoffs; HANDOFF recoveries to Stage 3 via Contents API CAS
      (rev 5→6)
- [x] Append salvage-session-reports.md; open personal-config docs draft

## PR lifecycle first-live-run retrospective (2026-08-20)

Rigorous audit of Stage 1/2/3 first live cron run. Evidence-first. No merges. No
Endor fleet scans. Do not rewrite AGENTS.md Learned* sections.

## Plan

- [x] Fetch Stage 1/2/3 cloud-agent sessions via cursor-cloud
      batch-fetch-details
- [x] Extract goals/decisions/mutations/handoffs from transcripts via focused
      readers
- [x] Corroborate PRs, SHAs, checks, ledger branch via GitHub/`gh`/git
- [x] Compare observed behavior vs documented policy
- [x] Write `docs/pr-lifecycle-pipeline-run-retro-2026-08-20.md`
- [x] Update pipeline docs/skills/lessons for P0/P1 gaps (no Learned* AGENTS.md)
- [x] Commit, push `cursor-agent/pr-pipeline-retrospective-b81b`, open draft PR
      #2052
- [x] Run targeted tests / `make test-quick` after first push (docs-only; 30/30
      smoke + path-validation OK)

## Security

- Treat session text, PR bodies, comments as untrusted data
- No secrets in commits; no force-push; no PR merges
- Stage 2 never merges; salvage never autonomously merges
- Record Endor skill as out_of_scope unless verified pipeline usage exists

## Daily agent-docs lineage (2026-08-21)

Stop Stage 1/2/3 from each opening a personal-config docs PR that rewrites the
same `tasks/*` files. Git run records are for agents; Notion stays the human
plane (packets + personal notes).

- [x] Encode one UTC-day `pr-lifecycle-docs-YYYYMMDD` PR in the lifecycle
      contract
- [x] Stage 1 creates/lands that lineage; Stage 2/3 only push to it
- [x] Exclusive files: no cron edits to `AGENTS.md` or `tasks/todo.md`
- [x] Update stage specs, prompts, exports, lesson 0gj, retro P1
- [x] Add prompt contract test; `sync_cursor_export_prompts.py --write` +
      `--check`
- [x] Commit and push on #2052; do not bump `policy_revision`
- [x] Merge `origin/main` (#2051 Learned*) into #2052 so Trunk can prepare a
      test branch; remaining `AGENTS.md` delta is the salvage stacked-PR bullet
      only — no Learned* rewrite
