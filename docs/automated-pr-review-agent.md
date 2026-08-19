# Automated PR Review & Consolidation Agent

**Version:** 1.2 **Compatibility:** Security-First Development Agent v3.0
**Scope:** Triage, review, edit, merge, and close PRs from automated agents
(Jules, Dependabot, Renovate, custom bots) across multiple repositories.

## Mission

Reduce PR accumulation from automated agents by triaging, reviewing,
consolidating, and resolving bot-authored PRs—merging the good, fixing the
fixable, and closing the rest. Act autonomously on routine decisions; escalate
when a PR crosses a defined trust boundary.

**In scope:** PRs whose GitHub API `login` or `app_slug` exactly matches a
configured, versioned bot identity (see [Configuration](#configuration)). Never
infer bot authorship from a title, branch, body, comment, or review history. An
ambiguous identity is human-authored for autonomous-action purposes. Stage 1 may
analyze a human-authored PR and record evidence, but it never autonomously
approves, merges, or closes it. _(Note: The agent is now exclusively responsible
for first-interaction contributor greetings, as legacy greeting workflows have
been disabled)._

## Preflight gate (mandatory)

**A fetched runtime ledger validated with
`python3 scripts/validate_pr_lifecycle_artifacts.py "$RUNTIME_LEDGER_PATH"` and
preflight must pass before any triage or write actions.** Fetch
`automation/pr-lifecycle-ledger:pr-lifecycle-ledger.yaml` first; the main-branch
`tasks/pr-lifecycle-ledger.yaml` file is a bootstrap pointer and never runtime
state. If either check fails or the runtime branch is absent, the session must
not proceed to inventory, merge, or close.

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
2. **Continuity read:** Read the last three Stage 1 run records and all
   Stage-1-owned entries in the
   [Automated PR Lifecycle Contract](automated-pr-lifecycle.md). Do not repeat
   an unchanged, unexpired action owned by another stage.
3. **Output:** Write full inventory to `tasks/pr-inventory.md` (table: Repo, PR
   #, Author, Category, CI, Conflicts, Age, Status).
4. **Classification:** Assign each PR exactly one category: `SECURITY`,
   `DEPENDENCY`, `PERFORMANCE`, `UI`, `REFACTOR`, `FEATURE`, `CI/INFRA`.
5. **Duplicate & overlap:** Detect exact duplicates (>90% file overlap),
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

| Disposition        | Criteria                                       | Action                           |
| ------------------ | ---------------------------------------------- | -------------------------------- |
| MERGE              | All gates pass, CI green, no conflicts         | Squash-merge, delete branch      |
| MERGE-AFTER-FIX    | Minor issues auto-fixed                        | Push fix, re-run CI, then merge  |
| REQUEST-CHANGES    | Issues beyond auto-fix                         | Post review, assign to human     |
| ESCALATE           | Security gate failure or architectural concern | Tag human, block merge           |
| CLOSE-DUPLICATE    | Duplicate or superseded                        | Close with linked explanation    |
| CLOSE-STALE        | Stale per config threshold                     | Close with reopen instructions   |
| CONSOLIDATE        | Multiple small PRs should be one               | See consolidation protocol below |
| HANDOFF-SALVAGE    | One bounded mechanical recovery is required    | Create a Stage 2 ledger handoff  |
| HANDOFF-COMPLETION | Policy, platform, canonical, or evidence hold  | Create a Stage 3 ledger handoff  |

**Consolidation:** Create branch `chore/consolidated-[category]-updates` from
main, cherry-pick or reapply changes, resolve conflicts, run tests, open one PR
listing original PRs, close constituents with link.

**Merge ordering:** Eligible routine dependency, CI/infra, refactor, UI, and
test/format work follows the current repository merge method. Security-sensitive
work is never automatically merged and is routed to Stage 3/human decision.
After each completion, re-check remaining PRs for new conflicts.

## Phase 4 — Reporting & Learning

- Write session report by appending to `tasks/review-session-reports.md` (repos
  processed, actions taken, escalations, consolidations, patterns, metrics).
  Optionally also add a point-in-time snapshot as
  `tasks/pr-review-YYYY-MM-DD.md` when a standalone dated file is needed.
- Update the lifecycle ledger for every item currently owned by Stage 1, using
  the shared anchors, outcome, next owner, safe default, evidence, and bounded
  next action. A base or head SHA change must invalidate evidence and return the
  item to Stage 1 intake.
- Update `tasks/lessons.md` with new patterns (bot behaviors, repo quirks,
  effective heuristics). Optionally reflect material lessons in
  [Review heuristics](#review-heuristics) below.

### Conflict-proofing write boundaries

- Review automation writes only to `tasks/review-session-reports.md` and the
  Stage-1-owned entries in the fetched
  `automation/pr-lifecycle-ledger:pr-lifecycle-ledger.yaml` runtime ledger. The
  main-branch `tasks/pr-lifecycle-ledger.yaml` bootstrap pointer is never
  written as state.
- Review automation must not write to `tasks/salvage-session-reports.md`.
- Canonical policy docs are read-mostly; only update for policy/version changes.

## Phase 5 — Hand off the nonterminal tail

Phase 1 is throughput-optimized: it merges what is clean, closes what is
redundant, and gives every remaining item one next owner. It must not leave a
prose-only deferred tail. Use the
[Automated PR Lifecycle Contract](automated-pr-lifecycle.md) to route a bounded
mechanical recovery to Stage 2 and an evidence, policy, platform, canonical, or
security hold to Stage 3.

When this skill finishes, append a Stage 1 run record and a ledger handoff. Each
handoff must include repository, PR, base/head SHA, author type, classification,
risk class, guardrail outcome, evidence, safe default, next action, and expiry.
Trigger Stage 2 only for one bounded repair. Trigger Stage 3 for all other
nonterminal work, including policy/security questions, unavailable platform
evidence, canonical conflicts, and unverified close candidates.

Stage 2 produces one or more **draft** salvage / infra-fix PRs; it does not
close a security original merely because a replacement draft exists. Stage 3
owns later reconciliation and completion. Review automation must not write to
`tasks/salvage-session-reports.md`. If a deferred PR is blocked by CodeScene
code health, Stage 2 must confirm `/cs-agent skill:fix-code-health-degradations`
was posted (or post it) before making final salvage/closure disposition.

### Legacy disposition map and compatibility

Historical reports remain evidence inputs under the lifecycle import procedure.
Their legacy values map as follows: `ESCALATE` becomes Stage 3 with
`REVIEW_SECURITY`, `HOLD_CONTRACT`, or the evidence-derived guardrail outcome;
`DEFER` becomes Stage 2 only with one complete Stage 2 work item, otherwise
Stage 3; `DIRTY` becomes a Stage 2 candidate only with bounded repair scope,
otherwise Stage 3; `UNSTABLE` becomes `HOLD_EVIDENCE` and Stage 3
reconciliation; and `CLOSE-DUPLICATE` becomes `CLOSED_DUPLICATE` or
`CLOSED_SUPERSEDED` only after canonical evidence and the appropriate cooldown.

The Stage 1 handoff must preserve the legacy deferred-tail inputs required for
recovery: trigger/check evidence, immutable source/base anchors, changed and
prohibited paths, root-cause/infra observation, proposed repair, required test
command/result, attempts and failed approach, provenance/canonical relation,
expiry, and one safe default. A prose report that lacks those inputs remains
evidence-only; it cannot directly trigger a Stage 2 branch.

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
- **identity_classification** and **sensitive_path_taxonomy:** versioned sources
  that keep ambiguous identities human and sensitive-path classification sticky.
- **lifecycle.policy_inputs:** identity, sensitive-path, permission,
  required-check, merge-method, and prompt revision identifiers.
- **lifecycle.stage_caps** and **lifecycle.stages:** the reviewed capacity,
  schedule, concurrency, and authority contract. Legacy merge, auto-fix, and
  escalation keys are prohibited by validation.

## Review heuristics

Apply these during classification and review (see also `tasks/lessons.md`):

- **PR Visual Recap (optional enrichment):** When a sticky comment marked
  `<!-- pr-visual-recap -->` (or titled “Visual recap”) exists, read it and the
  linked plan URL / screenshots as a **high-level change summary** during Gate
  1–3 review. Useful for large diffs, UI/docs-heavy PRs, and explaining intent
  in consolidation comments. **Do not** trigger or re-label `visual-recap` on
  every inventory PR — that burns Mistral/API quota. Only request a refresh
  (label `visual-recap` or Actions re-run) for a complex ESCALATE/DEFER case
  when the sticky is missing/stale and budget allows. Workflow:
  `.github/workflows/pr-visual-recap.yml`; backends:
  `docs/pr-visual-recap-agent-backends.md`.
- **Zero-diff / superseded:** Detect early (`changed_files_count == 0` or no
  effective diff); create a non-security closure candidate only when identity,
  anchors, canonical evidence, and the applicable cooldown are complete. Stage 3
  completes eligible closures after calibration. Never mark a draft ready as a
  shortcut around the stage contract.
- **Post-merge conflict cascade (Lesson 0):** Re-check mergeable state after
  each merge before proceeding. PRs touching the same hot file (`main.py`,
  `payload.json`, etc.) frequently flip to DIRTY after a sibling merge — defer
  with an explicit comment rather than force-push.
- **Stacked sibling PRs (`gh-stack`, Lesson 0ez):** When 2+ open PRs in the same
  repo collide on the same file(s) and all pass their gates, link them into a
  stack with `gh stack link <bottom> <middle> <top>` (bottom = the one that
  should land first), then merge the **top** of the stack once. This avoids
  merging each sibling and having the rest flip DIRTY. **Stack merges are not
  `gh pr merge`/GraphQL `mergePullRequest`-compatible**: use
  `gh stack merge --yes` if the gh extension is installed, otherwise the async
  REST API `PUT /repos/{owner}/{repo}/pulls/{top}/merge-async` + poll
  `.../merge-async/{uuid}` until `status=merged`. Auto-merge is unsupported for
  stacks. See AGENTS.md → `Stacked PRs during
  review/salvage sessions` for the
  full recipe.
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

The Review Agent is Stage 1 of the scheduled lifecycle. It runs at `0 15 * * *`
UTC with one concurrent run and a 20-item inventory cap. It is followed by Stage
2 at `0 17 * * *` and Stage 3 at `0 19 * * *`. See
[Three-Stage PR Lifecycle in Cursor Automations](cursor-automations/three-stage-pr-lifecycle.md).

### Daily Automation Chain

This agent operates within a broader daily automation workflow. The following
scheduled tasks run automatically each day on all seven priority repositories:

1. **6:00 AM** -
   [GitHub PR Summarizer](https://github.com/abhimehro/personal-config/tree/main/skills/github-pr-summarizer)
   - Creates daily PR summary reports in Notion's "GitHub PRs Daily Reports"
     database
   - Provides foundational context for all downstream agents
   - Runs before all other automations to ensure fresh documentation

2. **8:00 AM** - Proactive issue creation task

3. **8:15 AM** -
   [Repository Health Triage](https://github.com/abhimehro/personal-config/tree/main/skills/repo-health-triage)
   - Scans for security issues, risky code patterns, dependency problems
   - Creates issue candidates in Notion's "Repo Issue Candidates" database
   - Analyzes all seven repositories: personal-config, ctrld-sync,
     email-security-pipeline, Seatek_Analysis,
     Hydrograph_Versus_Seatek_Sensors_Project,
     series_correction_project_updated, repoprompt-ce

4. **9:00 AM** - PR automation test

5. **15:00 UTC** - Stage 1 Daily PR Review

6. **17:00 UTC** - Stage 2 Daily PR Salvage

7. **19:00 UTC** - Stage 3 Daily PR Completion

**Note:** Stage 1, Stage 2, and Stage 3 are the scheduled Cursor Dashboard PR
lifecycle automations. The 06:00 PR summary, 08:00 issue creation, 08:15
repository health, and 09:00 test jobs are upstream inputs only; they are not a
second review-and-merge chain.

### Weekly health & housekeeping (non-overlapping)

Separate Cursor Automations cover repository health, docs, and upkeep twice
weekly (Research repos Monday 10:00; General repos Thursday 10:00). Those runs
explicitly exclude security triage and PR review/salvage. Spec:
[docs/cursor-automations/weekly-repo-health.md](cursor-automations/weekly-repo-health.md).

## Related docs

- [Automated PR Salvage & Recovery Agent](automated-pr-salvage-agent.md) — Phase
  2 (the downstream skill that recovers the deferred / escalated tail this skill
  produces).
- [Automated PR Completion Agent](automated-pr-completion-agent.md) — Stage 3
  owner of nonterminal backlog reconciliation and bounded completion.
- [Automated PR Lifecycle Contract](automated-pr-lifecycle.md) — shared states,
  ledger, handoffs, and continuity rules.
- [GitHub App Permission Checklist](github-app-pr-automation-checklist.md) —
  Permissions, preflight, probe PRs, runbook.
- [PR Review Automation ELIR](pr-review-automation-elir.md) — Handoff summary
  for maintainers.
- [Repository Health Triage Skill](../../skills/repo-health-triage/SKILL.md) —
  Daily repo health scanning and issue triage.
- [GitHub PR Summarizer Skill](../../skills/github-pr-summarizer/SKILL.md) —
  Daily PR summary generation for non-technical audiences.
