# Automated PR Salvage & Recovery Agent

**Version:** 1.0 **Compatibility:** Security-First Development Agent v3.0; pairs
with
[Automated PR Review & Consolidation Agent v1.0](automated-pr-review-agent.md).
**Scope:** Investigate, recover, and rationalize the deferred / escalated tail
of a PR Review Agent session â i.e. PRs that the Review Agent could **not**
safely merge or close because they were `DIRTY`, `UNSTABLE`, blocked by a trust
boundary, or blocked by an infrastructure failure on `main`.

## Mission

The Review Agent (Phase 1) is optimized for _throughput_ â merge what's clean,
close what's redundant, and surface the rest. The Salvage Agent (Phase 2) is
optimized for _recovery_ â drive every PR in that surfaced tail to a final state
by either:

- **Salvaging** the legitimate work onto a fresh branch from `main` and opening
  a clean draft PR, then closing the original; or
- **Closing as superseded** when the work has already landed on `main` via a
  different PR; or
- **Diagnosing and fixing root-cause infrastructure breakage on `main`** that is
  blocking the PR (and possibly an entire repo's queue).

The Salvage Agent **never** autonomously merges anything. Every output is a
draft PR that a human maintainer reviews and merges. This is non-negotiable:
salvage operations touch source code in non-trivial ways (cherry-picks, conflict
resolution, test adaptation, file reverts) and must not bypass human judgment.

---

## Why a separate skill rather than an addendum

| Concern                        | Phase 1 â Review Agent                                                             | Phase 2 â Salvage Agent                                                                                         |
| ------------------------------ | ---------------------------------------------------------------------------------- | --------------------------------------------------------------------------------------------------------------- |
| Trigger                        | A scheduled or on-demand run over **all open PRs in scope**                        | An investigation of **a known list of deferred / escalated PRs** (e.g. from this morning's Phase-1 report)      |
| Throughput vs depth            | Shallow per PR (read description, diff, CI rollup, decide)                         | Deep per PR (clone repo, compare against current `main`, attempt rebase, inspect history, write or adapt tests) |
| Merge authority                | May squash-merge clean PRs autonomously                                            | **Never** merges autonomously; every output is draft                                                            |
| Output                         | Merges, closes, escalation comments                                                | New draft PRs (salvage), supersede-closes, infra-fix PRs                                                        |
| Failure mode if rules conflate | Routine auto-merge becomes risky; deep-dive becomes too slow to run on every cycle | â (separation removes the ambiguity)                                                                            |
| Preflight                      | Read-only `gh auth` + repo list check                                              | Same as Phase 1 + ability to clone repos and push new branches                                                  |

The two skills share the same config file (`tasks/pr-review-agent.config.yaml`)
and the same task-tracking files. Phase 2 reads the **"Post-session remainder"**
/ **"Escalated"** / **"Deferred"** sections of Phase 1's output as its input.

---

## Trigger conditions (when to run Phase 2)

Run the Salvage Agent when **any** of the following are true after a Phase 1
cycle:

1. The Phase 1 report has at least one PR in **`ESCALATE`** disposition.
2. The Phase 1 report has at least one PR in **`DEFER`** disposition that is
   **older than 24 hours** (a fresh `DIRTY` from this morning's cascade may
   resolve itself; a `DIRTY` that's been sitting for a day usually won't).
3. A **whole-repo CI failure on `main`** is suspected (e.g. 4+ open PRs in the
   same repo show the same failing required check, and that check has been
   failing on `main` since at least one merge ago â see Lesson 0t).
4. The maintainer flags a specific PR for "is this still salvageable?" review
   (e.g. via a label, a comment mentioning the agent, or a direct request).

**Do not** trigger Phase 2 just because a Phase 1 cycle had merges or closures â
that's normal Phase 1 output and doesn't require deep investigation.

**Do not** trigger Phase 2 on a stale snapshot. Always re-fetch the open PR list
from GitHub at the start of a Phase 2 run; deferred PRs may have already been
resolved (rebased by a human, closed, or merged via the UI) since the Phase 1
report was written.

---

## Inputs

| Input                                       | Source                                                                                                                                    | Required? | Notes                                                                                                                                                                       |
| ------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------- | --------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Configured repos                            | `tasks/pr-review-agent.config.yaml`                                                                                                       | yes       | Same field as Phase 1.                                                                                                                                                      |
| Bot authors / automation patterns           | `tasks/pr-review-agent.config.yaml`                                                                                                       | yes       | Same as Phase 1.                                                                                                                                                            |
| List of PRs to investigate                  | Phase 1 report (`tasks/pr-review-YYYY-MM-DD.md` "Post-session remainder" section) **or** explicit override list passed at invocation time | yes       | If invoked without an explicit list, use the most recent dated session report's deferred/escalated tail.                                                                    |
| Live PR state                               | GitHub API at run time                                                                                                                    | yes       | Re-fetch â never trust the snapshot in the Phase 1 report alone.                                                                                                            |
| Repo working clones                         | Cloned at run time into a scratch directory (e.g. `/tmp/salvage/<repo>`)                                                                  | yes       | Need read **and** write access â Salvage opens new branches and pushes them.                                                                                                |
| `GH_TOKEN` with push + PR-create permission | Env var                                                                                                                                   | yes       | If `git push` would otherwise pick a read-only bot credential, override the remote URL with `https://x-access-token:${GH_TOKEN}@github.com/<owner>/<repo>.git` (Lesson 0j). |

## Outputs

| Output                                                     | Where written                                                                                                         | Format                                                                                                                    |
| ---------------------------------------------------------- | --------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------- |
| Salvage PRs (one per recoverable original)                 | New branches `cursor-agent/salvage-<repo>-<old_pr>-<short_label>-<suffix>` on each affected repo, opened as **draft** | `gh pr create --draft`                                                                                                    |
| Infra-fix PRs (one per repo whose `main` needs unblocking) | Same naming pattern: `cursor-agent/fix-<short_label>-<suffix>`                                                        | `gh pr create --draft`                                                                                                    |
| Closure comments on superseded / blocked-by originals      | Inline PR comments with cross-link to either the salvage PR or the existing-on-main commit                            | `gh pr close --comment "..."` or `gh pr comment`                                                                          |
| Salvage session report                                     | Append to `tasks/salvage-session-reports.md` under a `## Run â YYYY-MM-DD` heading                                    | Markdown table with `Repo`, `Old PR`, `Disposition`, `New PR`, `Notes` columns + a counts summary + new patterns observed |
| New lessons                                                | Append to `tasks/lessons.md`                                                                                          | One numbered lesson per new pattern (Pattern â Rule â Detection cost)                                                     |

### Conflict-proofing write boundaries

- Salvage automation writes only to `tasks/salvage-session-reports.md`.
- Salvage automation must not write to `tasks/review-session-reports.md`.
- Canonical policy docs are read-mostly; only update for policy/version changes.

## Handoff points

After a Phase 2 run finishes, the human maintainer is expected to:

1. Review the new draft PRs in priority order: **infra-fix PRs first** (they
   unblock other PRs), then security-classified salvages (Sentinel /
   CWE-tagged), then perf / UX / chore salvages.
2. For each, verify the ELIR block in the PR description, run the verification
   commands listed there, and either merge (squash) or request changes.
3. After merging an infra-fix PR, run
   **`gh api -X PUT repos/<owner>/<repo>/pulls/<pr>/update-branch`** on each
   blocked-by PR and let CI re-run; then re-trigger Phase 1 on that repo to
   merge what's now clean.
4. If a salvage PR's verification step fails, leave a review comment on the
   salvage PR (not the original â the original is already closed).

The agent is expected to never:

- Merge a salvage PR or an infra-fix PR autonomously.
- Force-push to any branch.
- Push to a branch the agent did not create.
- Re-open a PR that was closed by the maintainer.

---

## Phase 2 workflow

### Step 0 â Preflight (mandatory)

Same preflight as Phase 1: `gh auth status` confirms the active token, the
configured repo list resolves, and the canonical `make cursor-cloud-hooks` is
run on the personal-config repo so commit-message secret scanning works (Lesson
0r). If any preflight check fails, abort â do not silently fall back.

<!-- pragma: allowlist secret -->

### Step 1 â Re-fetch the deferred / escalated tail

Read the most recent `tasks/pr-review-YYYY-MM-DD.md` (or the override list
passed at invocation). For each PR in the deferred / escalated section, hit the
GitHub API:

- If the PR is now `MERGED` â drop it from the queue (a human or another agent
  already merged it).
- If the PR is now `CLOSED` (and not by this agent) â drop it from the queue.
- If the PR is `OPEN` and `MERGEABLE/CLEAN` â drop it from the queue and add a
  note to the addendum saying "auto-resolved since Phase 1; consider re-running
  Phase 1 to merge."
- Otherwise â keep it for investigation.

### Step 2 â Per-repo grouping and infra detection

Group the surviving queue by repo. For each repo, count how many open PRs share
the same failing required check. If 4+ PRs share the same failure **and** the
latest run of that check on `main` is also failing, classify the repo as
**infra-broken**:

1. Pause merging anything in that repo.
2. Run Step 3 (root-cause infra investigation) before Step 4 (per-PR salvage).
3. Mark the addendum entry for that repo as "Top escalation."

### Step 3 â Root-cause infrastructure investigation (only if Step 2 flagged a repo)

Goal: locate the single change on `main` that broke the required check, and
propose the smallest possible revert.

1. Fetch the failing job's log:
   `gh run view <run-id> --repo <repo> --log-failed`.
2. Identify the first error (often a `SyntaxError`, `ImportError`, or
   `ModuleNotFoundError`).
3. If the error is a `SyntaxError` at line 1 of a file, **try the JSON-blob
   hypothesis** (Lesson 0x): read the file and decode it with
   `codecs.decode(content, 'unicode_escape')`. If that produces valid Python,
   you've found a corrupted-blob commit. Otherwise, look at recent commits to
   that file with `git log --oneline -- <file>`.
4. **Decide between revert and re-author:**
   - If the offending commit's intended change can be re-authored in a small
     clean PR, prefer **revert + clean re-roll** over trying to fix the blob in
     place. The decoded-but-still-wrong file in Phase 2's ESP investigation lost
     ~547 lines of validated logic â re-authoring is safer.
   - If the offending commit has been built on top of by other commits, use
     `git show <bad_commit> -- <file>` to identify which earlier commit's
     version of the file should be restored, and revert just that one file.
5. Open a draft PR with title
   `fix(<area>): <one-line description> (revert PR #<N>) â unblocks <check> on main`.
   The body must include:
   - The full chain of impact (which PRs are blocked behind this).
   - The verification command (e.g. `python -m py_compile <file>` and
     `pytest --collect-only`).
   - An explicit note on the trade-off being reverted (e.g. "the perf
     optimization that #693 was _intended_ to deliver is also reverted; a clean
     re-roll can be opened as a separate PR once main is green").
   - The standard ELIR block.
6. Cross-link the infra-fix PR onto every blocked PR with a comment:
   `**Blocked by #<infra_pr>.** ... Once this lands, sync this branch with \`gh
   api -X PUT .../update-branch\` and re-run CI.`

### Step 4 â Per-PR salvage decision tree

For each surviving PR in the queue (after infra-broken repos are paused), run
this decision tree:

Before applying the tree, if CodeScene code health is a failing check on the PR,
post `/cs-agent skill:fix-code-health-degradations` (if not already present in
the thread) and wait for that run's result. Then continue with the salvage
decision based on the updated check state and diff.

```
read PR title, body, file list, and full diff
â
âââ Does main ALREADY contain the change this PR proposes?
â   â
â   âââ YES â CLOSE-SUPERSEDED with a comment naming the canonical commit / PR.
â   â        Skip; do not open a salvage PR.
â   â
â   âââ NO â continue.
â
âââ Does the PR's diff have any value worth keeping?
â   (functional change OR test addition OR doc improvement OR security
â    hardening that is NOT yet on main)
â   â
â   âââ NO â CLOSE as no-op with a comment explaining why.
â   â        (Common case: a reformatter PR whose `content.replace(...)`
â   â         targets are all gone.)
â   â
â   âââ YES â continue to salvage.
â
âââ Salvage path:
â   1. git checkout -b cursor-agent/salvage-<repo>-<old_pr>-<short_label>-<suffix> main
â   2. For each VALUABLE file in the original PR:
â        - if the file is a JOURNAL / APPEND-ONLY (.jules/*.md, CHANGELOG.md):
â            * extract only the new entry from the PR's diff
â            * APPEND it to main's current version (NEVER `git checkout pr -- file`
â              on a journal â Lesson 0y)
â        - else if the file's signature changed on main (e.g. a refactored function):
â            * adapt the change/test to main's actual API (Lesson 0z); use
â              `ast`-based isolated import for tests if the target script has
â              module-level side effects
â            * verify with the relevant unit-test command before committing
â        - else (clean cherry-pick):
â            * git checkout pr_branch -- path/to/file
â            * if the file is a journal, see the APPEND-ONLY branch above
â   3. python -m py_compile (or pytest, or repo-specific) verification
â   4. git commit with author preserved if cherry-picked, descriptive subject
â      `<type>(<scope>): <change> (salvages #<N>)`
â   5. git push -u origin <branch>      (use GH_TOKEN-injected remote URL)
â   6. gh pr create --draft with the standard ELIR
â   7. gh pr close <old_pr> --comment "Closing as **superseded by #<new_pr>** ..."
âââ done
```

### Step 5 â Document the salvage run

Append a section to `tasks/salvage-session-reports.md`. Optionally link the
corresponding Phase 1 snapshot (`tasks/pr-review-YYYY-MM-DD.md`) as input
context. Required content:

- A salvage-results table: `Repo | Old PR | Disposition | New PR | Notes`.
- Counts: deep-dived, salvaged, new infra-fix PR, closed as superseded / no-op,
  cross-linked blocked-by, net new draft PRs awaiting human review.
- New patterns observed â file each as a numbered lesson in `tasks/lessons.md`
  (one Pattern â Rule â Detection cost block per lesson).

Salvage automation must not write to `tasks/review-session-reports.md`.

---

## Safeguards

These exist to prevent the specific classes of mistakes Phase 2 is designed to
catch:

### S1 â No autonomous merges. Ever.

Every PR opened by the Salvage Agent is `--draft`. Every closure is paired with
a salvage PR or an existing-on-main reference. The agent does not merge a
salvage PR even when CI is green â that's the maintainer's call.

### S2 â Append-only protection for journal files

When a salvage touches `.jules/*.md`, `CHANGELOG.md`, `.jules/sentinel.md`,
`.jules/palette.md`, `.jules/bolt.md`, `tasks/lessons.md`, or any file matching
`*/CHANGELOG*`, the agent must:

1. **Never** apply `git checkout pr_branch -- <journal_file>`. That's how Lesson
   0y bugs happen.
2. Instead, extract only the new appended entry from the PR's diff (the lines
   after the last `\n##` heading on `main`'s version of the file).
3. Append that entry to `main`'s current version with a blank line separator.
4. Verify the resulting file is **strictly longer** than `main`'s version
   (line-count regression is a tripwire).

### S3 â JSON-blob detection on every "perf" PR that touches a single file > 5KB

Before salvaging, run `head -c 200 <file> | grep -E '\\\\n.{20,}\\\\n'` (or
equivalent). If the file appears to be a stringified blob, immediately switch to
**Step 3 (root-cause infrastructure investigation)** instead of treating it as a
normal salvage. The same check applies during normal Phase 1 review of any PR
that adds or replaces a single source file, but Phase 2 is the last line of
defense.

### S4 â Test adaptation, not test wholesale-checkout

When the PR being salvaged contains test files, **do not**
`git checkout pr -- tests/<file>` blindly. Instead:

1. Read the test file from the PR.
2. Compare each tested function/method against `main`'s current signature and
   call sites.
3. If signatures match â checkout is fine.
4. If signatures changed â rewrite the test to match `main`'s actual API.
5. Verify the rewritten test by running it locally.
6. Add at least one defense-in-depth assertion if the original was a
   single-property test.

### S5 â `update-branch` 422 disambiguation

When attempting to sync a deferred branch, distinguish the two `422` responses:

- `"There are no new commits on the base branch."` â benign; the branch is
  current.
- `"merge conflict between base and head"` â real conflict. Switch to the
  salvage path (apply only unique files onto a fresh branch from `main`); do
  **not** try interactive rebase on the original branch.

### S6 â Security-classified repo gates

For repos classified as security-sensitive in
`tasks/pr-review-agent.config.yaml` (currently: `email-security-pipeline`), the
agent must:

1. Never bypass a broken pytest gate even when the failure is on `main` and
   unrelated to the PR (Lesson 0bb).
2. Treat all salvage PRs as draft regardless of how trivial the change looks.
3. Surface the infra-fix PR as the **top** escalation for the next session.
4. When CodeScene fails, trigger `/cs-agent skill:fix-code-health-degradations`
   before drafting salvage changes so the remediation attempt is captured in PR
   history.
5. **PR Visual Recap (optional):** If the original PR has a sticky
   `<!-- pr-visual-recap -->` comment / plan URL, use it as a map of intent when
   deciding CLOSE-SUPERSEDED vs salvage and when writing the draft salvage PR
   body. Prefer consuming an existing recap over burning API quota. Only add
   label `visual-recap` (or re-run the workflow) when the sticky is missing and
   the salvage is large/ambiguous. See
   `docs/pr-visual-recap-agent-backends.md` and
   `.github/workflows/pr-visual-recap.yml`.

### S7 — Provenance preservation on cherry-picks

When salvaging via `git cherry-pick <commit>`, do not strip the original author.
The salvage commit message should mention `Refs: #<old_pr> (salvage source)` so
the audit trail back to the original automation agent's contribution is
preserved.

### S8 â Branch naming and isolation

Salvage branches use the prefix
**`cursor-agent/salvage-<repo>-<old_pr>-<short_label>-<suffix>`**. Infra-fix
branches use **`cursor-agent/fix-<short_label>-<suffix>`**. Never push to a
branch the agent did not create. Never delete a remote branch the agent did not
create. The `<suffix>` is the same per-agent suffix used by the Review Agent's
branch policy so cloud-agent branches are easily distinguishable.

### S9 â Force-push prohibition (with one bounded exception)

Never `git push --force` and never `git push --force-with-lease` to any
pre-existing branch. The bounded exception: a salvage branch that was just
created and pushed by the agent, and that the agent then locally amended (e.g.
to drop an unintended file from the commit), may be replaced via **delete +
re-push** â not via `--force`. If that's not possible (branch already has
reviewer comments), abandon the branch and create a new one with a `-v2` suffix.

---

## Interaction with human review

### When some PRs need human escalation but others don't

The salvage queue is heterogeneous. Most salvages are routine (cherry-pick the
perf optimization, adapt the test). A minority touch the trust boundary (PR
automation toolchain, `.github/scripts/`, secrets management, auth, payment, DB
migrations).

Default rule: **all salvage PRs are draft, but the addendum and per-PR comments
must clearly tier the urgency** so the maintainer knows what to look at first.
Suggested tiers:

| Tier                                | Examples                                                           | Maintainer review SLA                      |
| ----------------------------------- | ------------------------------------------------------------------ | ------------------------------------------ |
| **T0 â infra-fix**                  | `esp#723`-style reverts that unblock an entire repo's CI           | Within the same review session             |
| **T1 â security-sensitive salvage** | `sa#157`-style Sentinel fixes (info-leak, auth, secrets)           | Highest priority among salvage PRs         |
| **T2 â trust-boundary salvage**     | `pc#826`-style changes touching the PR automation toolchain itself | Always merge by hand, never via auto-merge |
| **T3 â routine salvage**            | `pc#825/827`, `cs#743`, `hg#148`-style perf / UX / test additions  | Normal review queue                        |

The agent surfaces the tier in the salvage PR title prefix when meaningful (e.g.
`fix(security): ...` for T1, `perf(adguard): ...` for T3). The addendum links to
T0/T1 PRs first.

### When the maintainer asks Phase 2 to redo or refine a salvage

Treat the request as a fresh invocation. Do **not** force-push the existing
salvage branch. Either:

- Open a follow-up branch with `-v2` suffix and a new PR that supersedes the
  original salvage; or
- If the change is one-line, ask the maintainer to apply it as a normal
  review-comment fix on the existing salvage PR.

### When a salvage PR is reviewed and rejected

If a maintainer closes a salvage PR without merging, the original PR (which the
agent had closed with a `superseded by #<salvage>` comment) is now orphaned. The
next Phase 2 run should:

1. Detect the orphaned original (look for closed PRs where the agent's last
   comment cited a salvage PR that was itself closed-without-merge).
2. Add a `tasks/lessons.md` entry capturing the rejection reason if the
   maintainer left a review comment.
3. Do **not** automatically re-open the original â the maintainer rejected the
   salvage for a reason; that reason almost always applies to the original too.

---

## Workflow improvements recommended for the next iteration

These came directly out of the 2026-04-26 deep-dive run and should be folded
into Phase 1 too where applicable:

1. **Add JSON-blob detection to the Phase 1 review gate.** Right now Phase 1
   catches it incidentally as `FAIL` CI. Adding a Phase-1 check on every PR that
   adds or rewrites a file > 5KB ("does the file appear to be a stringified
   blob?") would catch it at PR creation time, not after a maintainer notices
   pytest is red on `main` for two days.
2. **Add a `security_classified_repos` field to
   `tasks/pr-review-agent.config.yaml`.** Currently the never-bypass policy for
   `email-security-pipeline` is a Lesson 0bb implicit rule; making it
   config-driven means a future repo (e.g. a payments service) can opt in
   without code changes to the agent.
3. **Add a `journal_files` field to `tasks/pr-review-agent.config.yaml`.**
   Default value: `["**/.jules/*.md", "**/CHANGELOG*", "tasks/lessons.md"]`. The
   agent uses this list to enforce the S2 append-only protection and to skip
   these files when computing the "% of PR that's source code" heuristic for
   triage.
4. **Add a tripwire on `git diff --stat` line counts during salvage.** If a
   salvage operation results in a commit whose `diff --stat` shows a net
   negative line count on a journal file, abort the commit and surface the
   journal file for review.
5. **Cache the `gh api repos/<repo>/contents/<file>` response for the duration
   of a Phase 2 run.** The deep-dive made dozens of API calls re-fetching the
   same `main` versions of files; a per-repo file-content cache would cut
   runtime ~3Ã on a heavy run.
6. **Make the Phase 1 deferred-tail format explicit and parsable.** Right now
   Phase 2 reads the `tasks/pr-review-YYYY-MM-DD.md` "Post-session remainder"
   section by `grep`-style heuristics. Convert it to a small YAML block at the
   bottom of each Phase 1 report (`open_followups: - {repo, pr, reason}`) so
   Phase 2 has a stable input contract.
7. **Run Phase 2 within a few hours of Phase 1, not on a separate day.** The
   deeper the gap, the more likely deferred PRs have been hand-rebased / merged
   / closed by the maintainer in between, requiring more Step 1 reconciliation.
   Same-session Phase 1 â Phase 2 is the cheapest cycle.

---

## Hard boundaries (non-negotiable)

- â Never merge a salvage PR or an infra-fix PR autonomously, regardless of CI
  color.
- â Never force-push (the bounded delete-and-re-push for fresh agent-created
  branches is the only exception, per S9).
- â Never push to a branch the agent did not create.
- â Never re-open a PR that the maintainer closed.
- â Never apply `git checkout <pr_branch> -- <journal_file>` (Lesson 0y).
- â Never autonomously approve / `gh pr review --approve` a salvage PR (the
  agent might be a CODEOWNER on some repos; treat that as a privilege not to be
  exercised).
- â Never bypass a broken pytest gate on a security-classified repo (Lesson
  0bb).
- â Never modify `tasks/pr-review-agent.config.yaml` from inside the agent. The
  config is human-curated.

## Related docs

- [Automated PR Review & Consolidation Agent](automated-pr-review-agent.md) â
  Phase 1 (the upstream skill that produces Phase 2's input).
- [GitHub App Permission Checklist](github-app-pr-automation-checklist.md) â

## Related docs

- [Automated PR Review & Consolidation Agent](automated-pr-review-agent.md) —
  Phase 1 (the upstream skill that produces Phase 2's input).
- [GitHub App Permission Checklist](github-app-pr-automation-checklist.md) —
  Permissions, preflight, probe PRs, runbook.
- [PR Review Automation ELIR](pr-review-automation-elir.md) — Handoff summary
  for maintainers.
- [`tasks/lessons.md`](../tasks/lessons.md) — Lessons 0t, 0u, 0v, 0w, 0x, 0y,
  0z, 0aa, 0bb were all derived from the runs that motivated this skill.
- [Repository Health Triage Skill](../../skills/repo-health-triage/SKILL.md) —
  Daily repo health scanning and issue triage for all priority repositories.
- [GitHub PR Summarizer Skill](../../skills/github-pr-summarizer/SKILL.md) —
  Daily PR summary generation that provides foundational context for salvage operations.

### Daily Automation Context

This Salvage Agent (Phase 2) operates within a broader daily automation workflow.
The following scheduled tasks run automatically each day on all seven priority
repositories and may produce documents and issue candidates that this agent
should reference:

- **6:00 AM** - GitHub PR Summarizer: Creates daily PR summary reports in Notion
- **8:15 AM** - Repository Health Triage: Scans for security issues and creates issue candidates

Both scheduled tasks analyze the same seven repositories: personal-config,
ctrld-sync, email-security-pipeline, Seatek_Analysis,
Hydrograph_Versus_Seatek_Sensors_Project, series_correction_project_updated,
repoprompt-ce.

