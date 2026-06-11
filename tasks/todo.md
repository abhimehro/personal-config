# ABHI-965 — Rotate WebDAV password in 1Password — 2026-05-24

- [x] Add `media-streaming/scripts/rotate-media-webdav.sh` (op item edit + optional file/doc sync)
- [x] Document procedure in `docs/CREDENTIAL_ROTATION.md` and `media-streaming/BACKUP_RECOVERY.md`
- [x] Add `tests/test_rotate_webdav_credentials.sh`
- [ ] **Manual (macOS):** `eval "$(op signin)"` then `./media-streaming/scripts/rotate-media-webdav.sh --sync-legacy-document --restart-media`
- [ ] Update Infuse / remote clients with new password; verify `curl` against local WebDAV port

# ABHI-964 — Verify no hardcoded credentials remain in repo — 2026-05-24

- [x] Run `trufflehog filesystem . --only-verified` (0 verified secrets on 2026-05-24).
- [x] Grep sweep for hardcoded password literals outside tests/examples.
- [x] Confirm media-streaming `curl -u` docs use `${MEDIA_WEBDAV_PASS}` or credential-file substitution.
- [x] Add `scripts/verify-repo-auth-hygiene.sh` and `make verify-credentials` for repeatability.

# ABHI-956: Test CWE-94 fix with malicious payload — 2026-05-24

- [x] Locate remediation in `.github/workflows/copilot-setup-steps.yml`
- [x] Add regression tests (static YAML + env-binding simulation)
- [x] Run tests and confirm malicious payload cannot break out of `process.env.REQUEST`
- [x] Commit, push, open PR

# Security Remediation Sprint (ABHI-967) — 2026-05-24

- [x] Publish `docs/AI_AGENT_SECURITY_REMEDIATION_GUIDE.md` and `tasks/security-remediation-master-tracker.md`.
- [x] Add `tests/test_copilot_setup_workflow.py` (ABHI-929 / ABHI-955 / ABHI-956 static checks).
- [x] Add `tests/test_repo_credential_hygiene.sh` (ABHI-964 repo verification).
- [ ] **Human:** Rotate GitHub PAT + WebDAV password (ABHI-918, ABHI-954, ABHI-965).
- [ ] **email-security-pipeline:** Apply same CWE-94 fix for `copilot-setup-steps.yml` (ABHI-943).


# Security Fix: CWE-94 copilot-setup-steps.yml (ABHI-943) — 2026-05-24

- [x] Confirm remediation on `main` (PR #1037): env `REQUEST` + `process.env.REQUEST`
- [x] Add regression tests in `tests/test_copilot_setup_steps_workflow.py` (PR #1045)
- [x] Run `python3 -m unittest tests.test_copilot_setup_steps_workflow -v`

---

# Security Fix: Cleartext Password Logging in infuse-media-server.py — 2026-05-14

- [x] Replace auto-generated password printing with `getpass.getpass()` interactive prompt in `media-streaming/archive/scripts/infuse-media-server.py`.
- [x] Preserve non-TTY fail-fast behavior (require `--password` or `AUTH_PASS`).
- [x] Refactor `setup_authentication` into `_get_or_generate_user` and `_get_or_prompt_password` to reduce cognitive complexity.
- [x] Correct stale "Auto-generating a password" error message in non-TTY branch.
- [x] Handle `EOFError`/`KeyboardInterrupt` from `getpass.getpass()` with a graceful exit.

---

# Backlog Cleanup Orchestration — 2026-05-09

- [x] Interview scope: Phase 1 review-and-merge enabled; Phase 2 light salvage triage only.
- [x] Read local runbooks, lessons, and prior reports.
- [x] Run GitHub preflight for configured repos and verify sixth repo access explicitly.
- [x] Build live six-repo inventory with automation-signal expansion.
- [x] Execute safe Phase 1 merges/closures only after gates pass.
- [x] Document light salvage triage candidates without creating salvage branches.
- [x] Write a new dated addendum/run file and link it from the session report log.
- [x] Verify docs and summarize results.

---

# Backlog Cleanup Final Pass — 2026-05-10

- [x] Pull live state for all 6 repos and reconcile against 2026-05-09 action log.
- [x] Merge `series_correction#15` (salvage from prior run, sole-of-kind, CLEAN).
- [x] Close-superseded the Hydrograph #169/#170/#171 cluster (covered by merged #172).
- [x] Close-superseded `series_correction#13` (replaced by salvage #15).
- [x] Close-duplicate `personal-config#884` (twin of #867 per Lesson 0dd).
- [x] Close-superseded `personal-config#880` (intent absorbed by `60f7e904 fix(morning-brief)`).
- [x] Escalate trust-boundary PRs (`personal-config#901`; `email-security-pipeline#791/#793/#796`).
- [x] Close-stale Jules junk-fixture bleed PRs (`personal-config#831/#836/#840/#849/#862/#867/#869`).
- [x] Close-superseded `personal-config#858` (`os` import already absent on main).
- [x] Salvage `personal-config#911` → draft #916 (Bolt partition perf, /tmp clone).
- [x] Salvage `personal-config#899` → draft #917 (parse_inventory refactor + 22 tests, /tmp clone).
- [x] Salvage `personal-config#856` → draft #918 (check_summary tests merged into existing module, /tmp clone).
- [x] Close-superseded `ctrld-sync#771` (main now has dedicated `pluralize()` helper).
- [x] Close-stale `series_correction#11` (refactor PR; salvage aborted with 6 conflicts vs PR #10 tests).
- [x] Update legacy archive `tasks/pr-review-session-reports.md` with 2026-05-10 final cleanup section (active logs now split: `tasks/review-session-reports.md` + `tasks/salvage-session-reports.md`).
- [x] Write `tasks/pr-final-cleanup-2026-05-10.json` action log.

---

# Follow-up: Trunk + markdownlint@0.48.0 empty-stdout JSON parse bug (2026-05-09)

**Status:** Open. Discovered while committing the recovery + upstream-sync
batch on 2026-05-09 / 2026-05-10. Required `git commit --no-verify` plus
manual `trufflehog` / `git diff --check` / token-regex sweep as a
security-equivalent check.

**Repro:**

1. Stage any markdown file with no markdownlint findings.
2. `git commit -m "test"` (or `trunk check --filter=markdownlint --no-progress`).
3. Markdownlint emits an **empty stdout** instead of `[]` when there are no findings.
4. Trunk's JSON parser fails with `parse error at line 1, column 7: syntax error while parsing array - unexpected ':'; expected ']'` (the parser falls through to the next pipeline stage's output and chokes there).
5. Hook reports `1 failure, no issues` and blocks the commit.

**Impact:** Every markdown commit on macOS where the markdownlint tool
is at v0.48.0 must use `--no-verify` and run security checks manually.
Defeats the purpose of the pre-commit hook for markdown-only changes.

**Proposed fixes (pick one):**

- File upstream against `trunk-io/plugins` describing the empty-stdout
  vs `[]` discrepancy and asking either Trunk or markdownlint to be
  tolerant.
- Pin `markdownlint` in `.trunk/trunk.yaml` to a version where `--json`
  emits `[]` on clean runs (verify locally before pinning).
- Add a `.trunk/configs/.markdownlint.yaml` adjustment if it nudges the
  CLI into emitting `[]` (e.g., a mode flag).

**Also worth bundling into the same change:**

- Add a `prettier-ignore` for `.claude/skills/**/SKILL.md` since those
  files are auto-managed by RepoPrompt (`repoprompt_managed: true`) and
  fighting prettier creates churn on the next sync.

**Acceptance:** A clean markdown-only commit succeeds without
`--no-verify` and with prettier untouching the auto-managed skill files.

---

# Demo Security Hardening — 2026-04-23

- [x] Add env-based Azure config + fail-fast validation in `copilot-demo/weather-assistant.ts`
- [x] Sanitize realtime error logging in `copilot-demo/weather-assistant.ts`
- [x] Revert root `package.json` to `{}` and keep dependencies in `copilot-demo/package.json`
- [x] Verify with TypeScript check in `copilot-demo`
- [x] Commit and push changes to `origin/main`

---

# Automation Expansion & PR Review Maintenance

## 1. Discovery & Verification

- [ ] **Check Jules Daily QA execution status** on `Seatek_Analysis` and `Hydrograph_Versus_Seatek_Sensors_Project`. _Success criteria: Green checkmark on the most recent run._
- [ ] **Fetch failing step logs** for `repository-automation-daily.yml` (the orchestrator workflow file) in `personal-config` to target the exact `quality-assurance` error configured in `.github/repository-automation.yml` (the config dictionary).

## 2. Infrastructure Cleanup

_Target Repositories: `personal-config`, `email-security-pipeline`, `ctrld-sync`, `Seatek_Analysis`, `Hydrograph_Versus_Seatek_Sensors_Project`_

- [ ] **Remove outright** `.github/workflows/greetings.yml` across all 5 repos.
- [ ] **Remove outright** `.github/workflows/changelog.yml` across all 5 repos.
- [ ] **Verify** no remaining composite actions or workflow dispatches reference the deleted files.

## 3. Workflow Modernization

- [ ] **Draft `release-drafter.yml`** for modern changelog generation, integrating it via independent configs tracking the default `main` branch.
- [ ] **Pin Supply Chain:** Lock `release-drafter/release-drafter` to a specific, verified commit SHA instead of the mutable `@v6` tag.
- [ ] **Update Documentation:** Modify `docs/automated-pr-review-agent.md` directly to explicitly state first-interaction routing is handled by the PR agent.

## 4. Fix personal-config Daily Automation

_(Blocked by Section 1: Proceed only after fetching actionable log data)_

- [ ] Address the `quality-assurance` bottleneck.
- [ ] If relying on a configuration waiver (bypassing the quality gate), ensure the waiver is explicitly documented to expire after 7 days or the next sprint review.

## 5. PR Review Session Execution

- [ ] Execute `scripts/run-pr-review-session.sh` in `personal-config`.
- [ ] Process output into `tasks/pr-inventory.md` and triage using `tasks/pr-triage.md`.
- [ ] Act on the inventory: Squash-merge passing PRs, consolidate trivial updates, and close stalemates.
- [ ] **Ambiguity Catch-all:** Flag ambiguous PRs in `tasks/pr-triage.md` with a `needs-discussion` label for manual resolution in the next cycle.

---

**Security Considerations & Trust Boundaries:**

- **Attack Surface Reduction:** Removing the legacy unmaintained `first-interaction` action shrinks supply-chain exposure.
- **Supply-Chain Hardening:** Pinning `release-drafter` to an immutable commit SHA prevents injection via compromised mutable tags.
- **Least-Privilege Authorization:** The `release-drafter.yml` workflow will be explicitly constrained to `permissions: { contents: write }` (no pull-request write vectors).
- **Assumptions:** The `run-pr-review-session.sh` enforces hard boundaries. No autonomous merges of code failing _Security Gate 2_ (as defined in `docs/automated-pr-review-agent.md`) will be permitted. _Zero-diff / superseded_ heuristic rules (also defined in `docs/automated-pr-review-agent.md`) will govern closure rationale.

- [x] Reproduce the eval injection vulnerability locally.
- [x] Root-cause the issue in `performance_optimizer.sh` and `smart_scheduler.sh`.
- [x] Implement subshell isolation to remove the insecure `eval` usages entirely.
- [x] Write/confirm unit tests pass to prevent regressions.
- [x] Review: Subshell effectively mitigates trap vulnerability.

- [x] Fixed code health failures and refactored PR categorization.