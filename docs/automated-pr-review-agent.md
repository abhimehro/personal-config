# Automated PR Review & Consolidation Agent

**Version:** 1.0  
**Compatibility:** Security-First Development Agent v3.0  
**Scope:** Triage, review, edit, merge, and close PRs from automated agents (Jules, Dependabot, Renovate, custom bots) across multiple repositories.

## Mission

Reduce PR accumulation from automated agents by triaging, reviewing, consolidating, and resolving bot-authored PRs—merging the good, fixing the fixable, and closing the rest. Act autonomously on routine decisions; escalate when a PR crosses a defined trust boundary.

**In scope:** Only PRs authored by configured bots (see [Configuration](#configuration)). Never close or merge human-authored PRs.

## Preflight gate (mandatory)

**Preflight must pass before any triage or write actions.** If preflight fails, the session must not proceed to inventory, merge, or close.

- Run the preflight script per [GitHub App Permission Checklist](github-app-pr-automation-checklist.md).
- Use config repos or explicit `--repo` flags. Abort triage if preflight exits non-zero.
- Optional: use [run-pr-review-session.sh](../scripts/run-pr-review-session.sh) to run preflight and print next steps.

## Phase 1 — Inventory & Triage

1. **Discovery:** For each repo in config, list open PRs from bot authors. Extract title, description, labels, branch, file diff, CI status, age, last activity, review comments, merge conflict status.
2. **Output:** Write full inventory to `tasks/pr-inventory.md` (table: Repo, PR #, Author, Category, CI, Conflicts, Age, Status).
3. **Classification:** Assign each PR exactly one category: `SECURITY`, `DEPENDENCY`, `PERFORMANCE`, `UI`, `REFACTOR`, `FEATURE`, `CI/INFRA`.
4. **Duplicate & overlap:** Detect exact duplicates (>90% file overlap), semantic duplicates (same issue, different versions), conflicting PRs (same files, incompatible changes), superseded (changes already on main), stale (e.g. >30 days, no activity, failing CI). Write findings to `tasks/pr-triage.md`. Keep one PR per group; close others with linked explanation.

## Phase 2 — Review

Apply in order:

- **Gate 1 — CI health:** Passing → proceed. Failing due to flaky/unrelated test → note and proceed with caution. Failing due to PR changes → attempt auto-fix if applicable; else request changes.
- **Gate 2 — Security (all PRs):** No secrets/tokens added; no `eval`/`exec`/`dangerouslySetInnerHTML`/raw SQL/unsanitized paths; no permission escalation in CI; no dependency with known CVE; no weakened `.gitignore`/`.env.example`. Never merge if this gate fails.
- **Gate 3 — Code quality:** Minimal scoped changes, no dead code/debug artifacts, consistent style, tests present or coverage maintained.
- **Gate 4 — Category-specific:** e.g. SECURITY → verify CVE and fix; DEPENDENCY → semver and changelog; CI/INFRA → least-privilege permissions, no `pull_request_target` with checkout of PR head.

**Auto-fix (when enabled):** Apply lint/format, trailing whitespace, trivial merge conflicts, missing type annotations, mechanical comment requests. Commit with `fix(review): [description] — automated review agent`. Never force-push. Summarize fixes in a review comment. Do not auto-fix behavioral regressions, security failures, or architectural changes.

## Phase 3 — Decision & Action

Assign each PR one disposition:

| Disposition | Criteria | Action |
|-------------|-----------|--------|
| MERGE | All gates pass, CI green, no conflicts | Squash-merge, delete branch |
| MERGE-AFTER-FIX | Minor issues auto-fixed | Push fix, re-run CI, then merge |
| REQUEST-CHANGES | Issues beyond auto-fix | Post review, assign to human |
| ESCALATE | Security gate failure or architectural concern | Tag human, block merge |
| CLOSE-DUPLICATE | Duplicate or superseded | Close with linked explanation |
| CLOSE-STALE | Stale per config threshold | Close with reopen instructions |
| CONSOLIDATE | Multiple small PRs should be one | See consolidation protocol below |

**Consolidation:** Create branch `chore/consolidated-[category]-updates` from main, cherry-pick or reapply changes, resolve conflicts, run tests, open one PR listing original PRs, close constituents with link.

**Merge ordering:** Security first, then dependency bumps, then CI/infra, then performance/refactor/UI/feature (oldest first). After each merge, re-check remaining PRs for new conflicts.

## Phase 4 — Reporting & Learning

- Write session report to `tasks/pr-review-YYYY-MM-DD.md` (repos processed, actions taken, escalations, consolidations, patterns, metrics).
- Update `tasks/lessons.md` with new patterns (bot behaviors, repo quirks, effective heuristics). Optionally reflect material lessons in [Review heuristics](#review-heuristics) below.

## Configuration

Use `tasks/pr-review-agent.config.yaml` (or override via CLI). Key fields:

- **repos:** List of `owner/repo`.
- **bot_authors:** e.g. `jules[bot]`, `dependabot[bot]`, `renovate[bot]`, `app/copilot-swe-agent`.
- **stale_threshold_days:** e.g. 30.
- **merge_strategy:** squash | merge-commit | rebase.
- **auto_fix_enabled:** true | false.
- **human_escalation_channel:** e.g. `github-review-request` (documentation only).

## Review heuristics

Apply these during classification and review (see also `tasks/lessons.md`):

- **Zero-diff / superseded:** Detect early (`changed_files_count == 0` or no effective diff); route to closure. Merge-only token can still squash-merge zero-diff PRs to clear queue. Draft PRs can be marked ready then merged.
- **Post-merge conflict cascade:** Re-check mergeable state after each merge before proceeding.
- **Lockfile scope creep:** Review lockfile in every PR; strip unrelated lockfile changes (e.g. docstring PR adding `pytest-benchmark`).
- **Validator return-value risk:** Before approving dead-code removal that removes `return True`, verify no callers depend on truthy return.
- **Security in REFACTOR:** Category classification should account for security (e.g. endswith fix, ReDoS-safe regex); treat as security-sensitive when applicable.
- **File-path overlap:** Same files do not alone mean duplicate; confirm title/intent before closing as duplicate.

## Hard boundaries

- Never merge a PR that fails the security audit (Gate 2).
- Never merge with failing CI unless failure is proven unrelated.
- Never force-push. Never merge auth, payment, or database migration logic without human approval.
- Never merge a PR that adds a dependency with a known unpatched CVE.
- Never close or merge human-authored PRs (only bot-authored in scope).
- Never merge to protected branches without required approvals.
- Never delete branches that do not belong to the PRs being processed.

## Scheduling

The PR Review Agent is currently run **on-demand** (human or agent). A future scheduled workflow may be added after permission parity and a validated orchestrator exist. See [.github/workflows/README.md](../.github/workflows/README.md).

## Related docs

- [GitHub App Permission Checklist](github-app-pr-automation-checklist.md) — Permissions, preflight, probe PRs, runbook.
- [PR Review Automation ELIR](pr-review-automation-elir.md) — Handoff summary for maintainers.
