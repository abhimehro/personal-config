# Automated PR Review & Consolidation Agent

**Version:** 1.0 **Compatibility:** Security-First Development Agent v3.0
**Scope:** Triage, review, edit, merge, and close PRs from automated agents
(Jules, Dependabot, Renovate, custom bots) across multiple repositories.

## Mission

Reduce PR accumulation from automated agents by triaging, reviewing,
consolidating, and resolving bot-authored PRs—merging the good, fixing the
fixable, and closing the rest. Act autonomously on routine decisions; escalate
when a PR crosses a defined trust boundary.

**In scope:** PRs authored by configured bots (see
[Configuration](#configuration)) **and** PRs that are **human-authored on
GitHub** but are clearly **automation-driven** (Jules / Sentinel / Bolt /
Palette / daily QA branches, `automation-workflow-*`, bot comments on the PR,
etc.). For these automation-driven PRs with a human author, you may triage,
review, and propose actions, but do **not** autonomously close or merge them
unless explicitly permitted by a higher-level policy. Never close or merge
**ordinary** human-authored PRs that lack automation signals. _(Note: The agent
is now exclusively responsible for first-interaction contributor greetings, as
legacy greeting workflows have been disabled)._

## Preflight gate (mandatory)

**Preflight must pass before any triage or write actions.** If preflight fails,
the session must not proceed to inventory, merge, or close.

- Run the preflight script per
  [GitHub App Permission Checklist](github-app-pr-automation-checklist.md).
- Use config repos or explicit `--repo` flags. Abort triage if preflight exits
  non-zero.
- Optional: use [run-pr-review-session.sh](../scripts/run-pr-review-session.sh)
  to run preflight and print next steps.

## Phase 1 — Inventory & Triage

1. **Discovery:** For each repo in config, list open PRs from bot authors.
   Extract title, description, labels, branch, file diff, CI status, age, last
   activity, review comments, merge conflict status.
2. **Output:** Write full inventory to `tasks/pr-inventory.md` (table: Repo, PR
   #, Author, Category, CI, Conflicts, Age, Status).
3. **Classification:** Assign each PR exactly one category: `SECURITY`,
   `DEPENDENCY`, `PERFORMANCE`, `UI`, `REFACTOR`, `FEATURE`, `CI/INFRA`.
4. **Duplicate & overlap:** Detect exact duplicates (>90% file overlap),
   semantic duplicates (same issue, different versions), conflicting PRs (same
   files, incompatible changes), superseded (changes already on main), stale
   (e.g. >30 days, no activity, failing CI). Write findings to
   `tasks/pr-triage.md`. Keep one PR per group; close others with linked
   explanation.

## Phase 2 — Review

Apply in order:

- **Gate 1 — CI health:** Passing → proceed. Failing due to flaky/unrelated test
  → note and proceed with caution. Failing due to PR changes → attempt auto-fix
  if applicable; else request changes.
- **CodeScene remediation trigger:** If the failing check includes CodeScene
  code health, post `/cs-agent skill:fix-code-health-degradations` on that PR
  before deferring. Re-check status after the CodeScene refactoring run
  completes and then continue Gate 1 triage.
- **Gate 2 — Security (all PRs):** No secrets/tokens added; no
  `eval`/`exec`/`dangerouslySetInnerHTML`/raw SQL/unsanitized paths; no
  permission escalation in CI; no dependency with known CVE; no weakened
  `.gitignore`/`.env.example`. Never merge if this gate fails.
- **Gate 3 — Code quality:** Minimal scoped changes, no dead code/debug
  artifacts, consistent style, tests present or coverage maintained.
- **Gate 4 — Category-specific:** e.g. SECURITY → verify CVE and fix; DEPENDENCY
  → semver and changelog; CI/INFRA → least-privilege permissions, no
  `pull_request_target` with checkout of PR head.

**Auto-fix (when enabled):** Apply lint/format, trailing whitespace, trivial
merge conflicts, missing type annotations, mechanical comment requests. Commit
with `fix(review): [description] — automated review agent`. Never force-push.
Summarize fixes in a review comment. Do not auto-fix behavioral regressions,
security failures, or architectural changes.

## Phase 3 — Decision & Action

Assign each PR one disposition:

| Disposition     | Criteria                                       | Action                           |
| --------------- | ---------------------------------------------- | -------------------------------- |
| MERGE           | All gates pass, CI green, no conflicts         | Squash-merge, delete branch      |
| MERGE-AFTER-FIX | Minor issues auto-fixed                        | Push fix, re-run CI, then merge  |
| REQUEST-CHANGES | Issues beyond auto-fix                         | Post review, assign to human     |
| ESCALATE        | Security gate failure or architectural concern | Tag human, block merge           |
| CLOSE-DUPLICATE | Duplicate or superseded                        | Close with linked explanation    |
| CLOSE-STALE     | Stale per config threshold                     | Close with reopen instructions   |
| CONSOLIDATE     | Multiple small PRs should be one               | See consolidation protocol below |

**Consolidation:** Create branch `chore/consolidated-[category]-updates` from
main, cherry-pick or reapply changes, resolve conflicts, run tests, open one PR
listing original PRs, close constituents with link.

**Merge ordering:** Security first, then dependency bumps, then CI/infra, then
performance/refactor/UI/feature (oldest first). After each merge, re-check
remaining PRs for new conflicts.

## Phase 4 — Reporting & Learning

- Write session report by appending to `tasks/review-session-reports.md` (repos
  processed, actions taken, escalations, consolidations, patterns, metrics).
  Optionally also add a point-in-time snapshot as
  `tasks/pr-review-YYYY-MM-DD.md` when a standalone dated file is needed.
- Update `tasks/lessons.md` with new patterns (bot behaviors, repo quirks,
  effective heuristics). Optionally reflect material lessons in
  [Review heuristics](#review-heuristics) below.

### Conflict-proofing write boundaries

- Review automation writes only to `tasks/review-session-reports.md`.
- Review automation must not write to `tasks/salvage-session-reports.md`.
- Canonical policy docs are read-mostly; only update for policy/version changes.

## Phase 5 — Hand off the deferred / escalated tail to the Salvage Agent

Phase 1 (this skill) is throughput-optimized: it merges what's clean, closes
what's redundant, and surfaces the rest. The deferred / escalated tail is
**explicitly out of scope here** — those PRs go to the
[Automated PR Salvage & Recovery Agent](automated-pr-salvage-agent.md) (Phase
2).

When this skill finishes a run, the deferred/escalated tail feeds Phase 2 input.
Record the run in `tasks/review-session-reports.md`, and when needed also emit a
dated snapshot (`tasks/pr-review-YYYY-MM-DD.md`) whose "Post-session remainder"
section is YAML-style with `repo`, `pr`, and `reason` fields per row. Trigger
Phase 2 when **any** of: ≥1 PR is `ESCALATE`, ≥1 PR has been `DEFER`'d for >24
h, or 4+ PRs in the same repo share the same failing required check (suspected
`main`-side infra breakage).

Phase 2 will produce one or more **draft** salvage / infra-fix PRs and close the
originals with cross-links. Phase 2 never merges autonomously. Review automation
must not write to `tasks/salvage-session-reports.md`. If a deferred PR is
blocked by CodeScene code health, Phase 2 must confirm
`/cs-agent skill:fix-code-health-degradations` was posted (or post it) before
making final salvage/closure disposition.

## Local Git, `gh`, and Jujitsu (jj)

- Prefer **`gh pr merge` / `gh pr comment` / GraphQL** for agent operations when
  tokens are injected as `GH_TOKEN`.
- If you also use **Jujitsu** or multiple `gh` host credentials, validate that
  **`git push` / `jj git push`** uses the **same write-capable PAT** as `gh`;
  otherwise branch updates can fail with **403** while merges still work. See
  [GitHub App Permission Checklist](github-app-pr-automation-checklist.md) §4.

## Configuration

Use `tasks/pr-review-agent.config.yaml` (or override via CLI). Key fields:

- **repos:** List of `owner/repo`.
- **bot_authors:** e.g. `jules[bot]`, `dependabot[bot]`, `renovate[bot]`,
  `app/copilot-swe-agent`.
- **stale_threshold_days:** e.g. 30.
- **merge_strategy:** squash | merge-commit | rebase.
- **auto_fix_enabled:** true | false.
- **human_escalation_channel:** e.g. `github-review-request` (documentation
  only).

## Review heuristics

Apply these during classification and review (see also `tasks/lessons.md`):

- **PR Visual Recap (optional enrichment):** When a sticky comment marked
  `<!-- pr-visual-recap -->` (or titled “Visual recap”) exists, read it and the
  linked plan URL / screenshots as a **high-level change summary** during Gate 1–3
  review. Useful for large diffs, UI/docs-heavy PRs, and explaining intent in
  consolidation comments. **Do not** trigger or re-label `visual-recap` on every
  inventory PR — that burns Mistral/API quota. Only request a refresh (label
  `visual-recap` or Actions re-run) for a complex ESCALATE/DEFER case when the
  sticky is missing/stale and budget allows. Workflow:
  `.github/workflows/pr-visual-recap.yml`; backends:
  `docs/pr-visual-recap-agent-backends.md`.
- **Zero-diff / superseded:** Detect early (`changed_files_count == 0` or no
  effective diff); route to closure. Merge-only token can still squash-merge
  zero-diff PRs to clear queue. Draft PRs can be marked ready then merged.
- **Post-merge conflict cascade (Lesson 0):** Re-check mergeable state after
  each merge before proceeding. PRs touching the same hot file (`main.py`,
  `payload.json`, etc.) frequently flip to DIRTY after a sibling merge — defer
  with an explicit comment rather than force-push.
- **Lockfile scope creep:** Review lockfile in every PR; strip unrelated
  lockfile changes (e.g. docstring PR adding `pytest-benchmark`).
- **Validator return-value risk:** Before approving dead-code removal that
  removes `return True`, verify no callers depend on truthy return.
- **Security in REFACTOR:** Category classification should account for security
  (e.g. endswith fix, ReDoS-safe regex); treat as security-sensitive when
  applicable.
- **File-path overlap:** Same files do not alone mean duplicate; confirm
  title/intent before closing as duplicate. Prefer explicit superset accounting
  in close comments (Lesson 0v).
- **Pre-existing CI infra breakage on `main` (Lesson 0t):** If the same required
  check fails on 4+ open PRs in the same repo **and** has failed on `main` since
  at least one merge ago, treat it as infra failure on `main` rather than
  per-PR. Defer all merges in that repo and surface a single top-priority
  escalation to fix the infra. Never bypass a broken security/test gate for a
  security-sensitive pipeline.
- **In-scope infra fixes (Lesson 0u):** Before deferring an entire repo, scan
  inventory for an in-scope PR whose diff also fixes the broken CI infra (e.g.
  requirements pin, workflow update, action SHA bump). Merge that PR first, then
  call `gh api -X PUT repos/$REPO/pulls/$PR/update-branch` on each sibling to
  re-run their checks against the fixed workflow. Re-evaluate mergeability and
  proceed with the normal merge order; close any sibling that becomes zero-diff
  per Lesson 0b.
- **Trust boundary on PR automation toolchain itself:** A PR that rewrites
  scripts in `tasks/`, `scripts/`, or `.github/scripts/` is touching the same
  toolchain the agent uses to act on PRs. Always escalate for human review even
  when the security intent is clear and CI is green.
- **Branch-protection introspection (Lesson 0w):**
  `gh api repos/$REPO/branches/main/protection` may return `403` for
  personal-account tokens. Treat this as benign for personal repos and rely on
  `gh pr merge` exit codes to detect protection-blocked merges.
  <!-- pragma: allowlist secret -->

## Hard boundaries

- Never merge a PR that fails the security audit (Gate 2).
- Never merge with failing CI unless failure is proven unrelated.
- Never force-push. Never merge auth, payment, or database migration logic
  without human approval.
- Never merge a PR that adds a dependency with a known unpatched CVE.
- Never close or merge human-authored PRs (only bot-authored in scope).
- Never merge to protected branches without required approvals.
- Never delete branches that do not belong to the PRs being processed.

## Scheduling

The PR Review Agent is currently run **on-demand** (human or agent). A future
scheduled workflow may be added after permission parity and a validated
orchestrator exist. See
[.github/workflows/README.md](../.github/workflows/README.md).

### Daily Automation Chain

This agent operates within a broader daily automation workflow. The following
scheduled tasks run automatically each day on all seven priority repositories:

1. **6:00 AM** - [GitHub PR Summarizer](https://github.com/abhimehro/personal-config/tree/main/skills/github-pr-summarizer)
   - Creates daily PR summary reports in Notion's "GitHub PRs Daily Reports" database
   - Provides foundational context for all downstream agents
   - Runs before all other automations to ensure fresh documentation

2. **8:00 AM** - Proactive issue creation task

3. **8:15 AM** - [Repository Health Triage](https://github.com/abhimehro/personal-config/tree/main/skills/repo-health-triage)
   - Scans for security issues, risky code patterns, dependency problems
   - Creates issue candidates in Notion's "Repo Issue Candidates" database
   - Analyzes all seven repositories: personal-config, ctrld-sync, email-security-pipeline, Seatek_Analysis, Hydrograph_Versus_Seatek_Sensors_Project, series_correction_project_updated, repoprompt-ce

4. **9:00 AM** - PR automation test

5. **1:00 PM** - Salvaging task

**Note:** This PR Review Agent (Phase 1) and the Salvage Agent (Phase 2) are
separate from the scheduled daily automations. The scheduled tasks provide
input documents and issue candidates that these agents can reference during
triage and salvage operations.

## Related docs

- [Automated PR Salvage & Recovery Agent](automated-pr-salvage-agent.md) — Phase
  2 (the downstream skill that recovers the deferred / escalated tail this skill
  produces).
- [GitHub App Permission Checklist](github-app-pr-automation-checklist.md) —
  Permissions, preflight, probe PRs, runbook.
- [PR Review Automation ELIR](pr-review-automation-elir.md) — Handoff summary
  for maintainers.
- [Repository Health Triage Skill](../../skills/repo-health-triage/SKILL.md) —
  Daily repo health scanning and issue triage.
- [GitHub PR Summarizer Skill](../../skills/github-pr-summarizer/SKILL.md) —
  Daily PR summary generation for non-technical audiences.
