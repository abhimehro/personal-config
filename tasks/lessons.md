# Lessons Learned

## Lesson 0cy: Sentinel security PR CI fail from stale branch test import (2026-07-05)

**Pattern:** personal-config #1500 (pgrep option injection fix) failed `Run All Tests` because the PR branch still had `tests/test_refactoring_agent_workflow.py` importing `pytest`, while `main` had already migrated the test to stdlib `unittest`/`yaml`. Security diff was only 4 shell files. **Rule:** Before deferring a security PR on unrelated CI failure, merge `origin/main` into the branch and re-run checks; if the failure is pre-existing drift on the branch, autofix-merge is safe. **Detection cost:** Low — CI log shows `ModuleNotFoundError: pytest` with zero pytest changes in PR diff.

## Lesson 0cz: repoprompt Style gate requires macOS SwiftFormat (2026-07-05)

**Pattern:** repoprompt-ce #91/#92 pass Build and Test but fail `Style` (SwiftFormat). Cloud Linux agent cannot run `make install-format-tools` (Homebrew required). **Rule:** DEFER Palette/Bolt Swift UI PRs with Style-only failures to macOS salvage (`make dev-format` / `make dev-lint`); do not merge with Style red. **Detection cost:** Low — Style fail + Build pass + `install_format_tools.sh` Homebrew error.

## Lesson 0cv: Codacy action bump ≠ Codacy scan green (2026-06-23)

**Pattern:** personal-config #1331 (codacy-analysis-cli-action 1.1.0 → 4.4.7) merged with passing CI, but **all** sibling open PRs still fail `Codacy Security Scan` on re-run. Other gates (CodeQL, Snyk, CodeScene, dependency-review) pass. **Rule:** Treat Codacy failures after an action bump as **ESCALATE** (project token, API config, or org-level Codacy settings)—not auto-fixable by further dependabot bumps alone. **Detection cost:** Low — single failing required check across entire PR queue.

## Lesson 0cw: ctrld dependabot cluster blocked by QA fix PR (2026-06-23)

**Pattern:** ctrld #938–#942 (workflow-only dependabot) fail `mypy`/`ruff` while #943 (Jules QA lint/type fixes) passes those jobs but fails CodeScene. Dependabot branches are already up-to-date with `main`. **Rule:** Merge order is #943 first (post CodeScene `/cs-agent`), then re-run CI on dependabot cluster—workflow bumps inherit lint state from `main`, not from their diffs. **Detection cost:** Low — mypy/ruff fail on zero-Python-file PRs.

## Lesson 0cx: Duplicate Bolt perf PRs — close younger subset (2026-06-23)

**Pattern:** hg #290/#291 and sc #142/#145 were same-intent Bolt optimizations opened hours apart; newer PR had broader diff + green CI. **Rule:** When two Bolt branches touch the same production file with >70% intent overlap, merge the PR with passing CI and more complete diff; close the other with link. **Detection cost:** Low — `gh pr diff --name-only` + title keyword match.

## Lesson 0ct: Security salvage must update test constants (2026-06-21)

**Pattern:** repoprompt-ce #23 (Keychain accessibility hardening) failed Build because `KeychainServiceTests` still asserted `kSecAttrAccessibleAfterFirstUnlock` while the salvage changed production code to `kSecAttrAccessibleWhenUnlockedThisDeviceOnly`. **Rule:** When salvaging security PRs that change Keychain/crypto constants, grep tests for the old constant and adapt assertions in the same salvage commit (S4). Open `-v2` salvage branch rather than force-pushing. **Detection cost:** Low — CI Build log shows `XCTAssertEqual` mismatch on accessibility string.

## Lesson 0cu: Mashed workflow YAML spreads across repos (2026-06-21)

**Pattern:** personal-config `main` had mashed duplicate `uses:` lines in six workflows; repoprompt-ce `dependency-review.yml` had the same defect, causing dependency-review failures on all open salvage PRs. pc #1304 attempted SHA→tag regression on top of existing corruption. **Rule:** On any workflow corruption ESCALATE, scan **all configured repos** for `uses:.*uses:` before closing the incident; open paired T0 infra-fix drafts per affected repo. **Detection cost:** Low — `rg 'uses:.*uses:' .github/workflows/` per repo.

## Lesson 0cr: automation-workflow-updates YAML corruption (2026-06-21)

**Pattern:** `automation-workflow-updates-*` branches from daily workflow consolidation can produce mashed duplicate `uses:` lines in YAML (e.g. `dependency-review.yml`, `stale.yml`) and regress SHA pins to mutable tags. CI may still pass if workflows are not exercised on the PR branch. **Rule:** Always run a YAML integrity scan on workflow-only PRs before merge; treat any duplicated `uses:` line or SHA→tag regression as **ESCALATE**, never auto-merge.

## Lesson 0cs: personal-config Bolt journal conflicts after sibling merge (2026-06-21)

**Pattern:** Squash-merging pc #1307 (`system_metrics.sh` + bolt.md journal) left pc #1308 (`repository_automation_tasks.py` + bolt.md) **CONFLICTING** on `.jules/bolt.md` only. **Rule:** After merging one Bolt PR that touches `bolt.md`, immediately merge `origin/main` into the next sibling Bolt PR before attempting squash-merge; resolve journal conflicts by taking `main` bolt.md and appending the PR's single learning entry (deduplicated).

## Lesson 0cq: ctrld journal PRs conflict after Bolt/Sentinel burst (2026-06-16)

**Pattern:** After squash-merging ctrld #905, #906, and #902 on the same day,
documentation-only #904 (`bolt journal` rule) and performance #901 flipped to
**DIRTY** even though both were green at session start. **Rule:** Merge
journal/docs-only Bolt PRs **before** or **immediately rebase** after a sibling
performance merge burst on `main.py`. Defer with a comment rather than
force-push; journal content is low-risk to recreate.

## Lesson 0x: ESP overlapping-file cluster — merge lint → UI → perf → QA (2026-06-09)

**Pattern:** Four email-security-pipeline PRs (#1054–#1060) touched overlapping
files (`spam_analyzer.py`, `setup_wizard.py`, `test_ui_palette.py`) with
distinct intents (lint, Palette colorize, URL Counter perf, Jules QA
formatting). **Rule:** Merge in ascending scope order: trivial lint first, then
UI/Palette, then substantive perf logic, then umbrella QA/formatting last.
Re-check mergeability after each squash-merge (Lesson 0).

## Lesson 0: Multi-repo automated PR merges need sequential re-validation

**Pattern:** After squash-merging one automation PR, sibling PRs from the same
bot often become **CONFLICTING** with `main`. **Rule:** Re-run mergeability
after each merge; merge `origin/main` into the PR branch and resolve conflicts
with ordinary commits (never force-push). Use `GH_TOKEN` on the git remote if
`gh` picks a bot credential that cannot push.

## Lesson 0a: Control D Pipeline Fix (2026-03-15)

## 1. Hardcoded paths break test isolation

**Pattern:** Scripts that hardcode `/etc/controld/...` fail in non-root test
environments. **Rule:** Always use `${CONTROLD_DIR:-/etc/controld}` for any path
under the controld config directory. Apply this consistently across all files
that reference the directory — not just the main script.

## 2. Generated TOML ≠ Dashboard Attribution

**Pattern:** `ctrld` generates a `ctrld.toml` on start regardless of how it was
invoked, but the `--cd <profile_id>` flag is what provides dashboard-level
attribution. **Rule:** Don't confuse the auto-generated local config with proof
of dashboard connectivity. The native `--cd` flag is the correct mechanism for
profile attribution.

## 3. Test mocks must cover new functions

**Pattern:** Introducing `restart_with_native_profile` broke
`test_controld_validation.sh` because only `restart_with_config` was mocked.
**Rule:** When adding a new function to the call path, immediately update all
test files that mock functions in that path.

## Lesson 0b: Zero-diff “security” PRs should be closed, not merged (2026-03-21)

**Pattern:** Automation opens a PR whose **body** describes fixes, but
`changedFiles == 0` and `gh pr diff` is empty—often because `main` already
contains the change. **Rule:** Close with a short comment linking the finding;
do not squash-merge empty commits. Saves queue noise and avoids misleading
“merged” history.

## Lesson 0c: Retry merge after “Base branch was modified” (2026-03-21)

**Pattern:** Squash-merging PR A updates `main`; immediate merge of PR B fails
with GraphQL _Base branch was modified_. **Rule:** Re-fetch mergeability and
retry B without force-push; no branch rewrite required.

## Lesson 0d: Cursor Cloud pre-commit hook + spaced secret names (2026-03-21)

**Pattern:** `pre-commit.cursor` used `SECRET_VALUE="${!SECRET_NAME}"`. Entries
in `CLOUD_AGENT_INJECTED_SECRET_NAMES` can be human-readable labels with spaces
(`GitHub SSH Key`), which are **not** valid bash identifier names →
`invalid variable name` at commit time. **Rule:** Resolve values with
`printenv "$SECRET_NAME"` (after trimming whitespace from comma-split tokens).
Canonical copies: `scripts/cursor_cloud_agent_pre_commit.sh` and
`scripts/cursor_cloud_agent_commit_msg.sh`.

## Lesson 0r: Injected Cloud hooks do not persist — sync from the repo (2026-04-11)

**Pattern:** Fixes applied only under `~/.cursor/agent-hooks/<hash>/` are **not
in git** and disappear on the next fresh Cloud workspace. Injected copies can
still use `${!SECRET_NAME}` and break commits when secret **labels** contain
spaces. **Rule:** After clone in Cursor Cloud, run **`make cursor-cloud-hooks`**
(or `./scripts/install_cursor_cloud_agent_hooks.sh`) so `pre-commit.cursor` and
`commit-msg.cursor` are overwritten from the canonical scripts in this
repository. The installer requires **both** files as **regular** (non-symlink)
paths and uses `install -m 0755` instead of `cp` to avoid symlink follow /
TOCTOU surprises.

## Lesson 0e: Jules “Bolt” PRs may ship 100k-line junk fixtures (2026-03-22)

**Pattern:** A performance-titled PR adds a multi-megabyte `test.txt` of
generated hostnames and scratch `test_perf*.py` files. **Rule:** Treat as
**merge blocker** (hygiene + abuse-of-repo signal). Require removal before any
squash-merge; do not assume good faith without a minimal reproducible benchmark
tied to `docs/TESTING.md` patterns.

## Lesson 0f: Emoji-heavy default branch names can break dependency-submission jobs (2026-03-22)

**Pattern:** `submit-pypi` / GitHub dependency snapshot action failed with
`HttpError` on a branch named with leading emoji after syncing `main` into a PR.
**Rule:** When `submit-pypi` fails only on bot branches, check for
**ref/encoding** issues before blaming application code; still treat as **merge
blocker** unless branch protection marks the job non-required.

## Lesson 0i: IDE background terminal stalling — root cause is 1Password SSH Agent (2026-03-24)

**Pattern:** All `run_command` calls from IDE agents stall indefinitely in repos
using 1Password SSH Agent, regardless of Fish prompt theme. Removing Hydro,
disabling gitnow, and setting `hydro_fetch false` did NOT fix it. The root cause
is 1Password's Touch ID gate: background terminals have no window to display the
biometric prompt, so auth blocks forever. This is a confirmed upstream bug
(1Password 8.12.x + Apple Keychain, still under investigation). **Mitigations
applied (layered):**

1. **SSH key pinning:** `IdentitiesOnly yes` +
   `IdentityFile "~/.ssh/GitHub SSH Key.pub"` in `Host github.com` block —
   reduces agent re-prompting.
2. **Tight timeouts:** `ServerAliveInterval 10`, `ConnectTimeout 10` —
   connections fail fast instead of hanging forever.
3. **Socket health check:** `config.fish` detects 1Password socket availability
   and falls back to macOS native agent.
4. **Agent API bypass:** Use GitHub MCP API (`mcp_GitHub_*` tools) for all
   PR/repo operations instead of `run_command`.

**Verified:** Hydro and gitnow were both eliminated as suspects through
systematic removal testing on 2026-03-24.

---

**Pattern:** Attempting to `gh pr review --request-changes` fails with
`Can not request changes on your own pull request` when the automation bot is
the same identity that opened the PR. **Rule:** Use `gh pr comment` to leave
feedback and manually request resolution instead of using the formal review
state for self-authored automated PRs.

## Lesson 0h: IDE background terminal stalling — root cause is 1Password SSH Agent (2026-03-24)

**Pattern:** All `run_command` calls from IDE agents stall indefinitely in repos
using 1Password SSH Agent, regardless of Fish prompt theme. Removing Hydro,
disabling gitnow, and setting `hydro_fetch false` did NOT fix it. The root cause
is 1Password's Touch ID gate: background terminals have no window to display the
biometric prompt, so auth blocks forever. This is a confirmed upstream bug
(1Password 8.12.x + Apple Keychain, still under investigation). **Mitigations
applied (layered):**

1. **SSH key pinning:** `IdentitiesOnly yes` +
   `IdentityFile "~/.ssh/GitHub SSH Key.pub"` in `Host github.com` block —
   reduces agent re-prompting.
2. **Tight timeouts:** `ServerAliveInterval 10`, `ConnectTimeout 10` —
   connections fail fast instead of hanging forever.
3. **Socket health check:** `config.fish` detects 1Password socket availability
   and falls back to macOS native agent.
4. **Agent API bypass:** Use GitHub MCP API (`mcp_GitHub_*` tools) for all
   PR/repo operations instead of `run_command`.

**Verified:** Hydro and gitnow were both eliminated as suspects through
systematic removal testing on 2026-03-24.

## Lesson 0k: `actions/labeler@v6` + `pull_request_target` reads **base** `labeler.yml` (2026-03-24)

**Pattern:** A PR updates `.github/labeler.yml` to a new structure, but the
`label` workflow still fails with
`found unexpected type for label 'documentation'`. **Root cause:** Workflows
using `on: pull_request_target` execute with workflow + config from the
**default branch**, not the PR head. Until `main`’s `.github/labeler.yml`
matches **labeler v5+ / v6** expectations, PRs will keep failing the label job.
**Rule:** When fixing labeler config for `pull_request_target`, patch **`main`
first** (or temporarily switch the workflow to `pull_request` for verification
per upstream README). Validate against the **array-of-match-objects** schema
from `actions/labeler` README — avoid over-nesting under `any-glob-to-any-file`.

## Lesson 0j: `git push` for PR branch updates must use the same credential as `gh` (2026-04-01)

**Pattern:** `gh pr merge` / API calls authenticate as the user via `GH_TOKEN`,
but a plain `git push https://github.com/owner/repo.git` may pick
**`cursor[bot]`** (or another secondary host entry) from
`~/.config/gh/hosts.yml`, producing **403 Permission denied** even when the user
can merge via UI/`gh`. **Rule:** After `gh auth setup-git`, verify `git push`
uses the **intended** identity, or avoid pushes entirely and use
**`gh pr merge`** / **`gh workflow run`** / **MCP**. For **Jujitsu (jj)**: treat
`jj git push` the same way — ensure remote credentials map to the
**human/maintenance PAT**, not a read-only bot. Prefer documenting: “PR branch
sync: `gh` API or PAT-in-URL remote,” not unauthenticated HTTPS.

## Lesson 0l: Inventory data can become stale - verify PR existence before triage (2026-04-03)

**Pattern:** PR inventory lists non-existent PRs (e.g., email-security-pipeline
#627) causing "Not Found" errors during merge attempts. **Rule:** Before adding
PRs to inventory or attempting merges, verify existence with `get_pull_request`.
Inventory should be treated as a snapshot that may drift.

## Lesson 0m: Merge order matters - security before performance (2026-04-03)

**Pattern:** Merging performance PRs first (e.g., Seatek #123) caused security
fixes (Seatek #120, #122) to become unmergeable due to conflicts. **Rule:** When
security and performance PRs touch the same files, merge security fixes first.
Performance optimizations can be rebased on top of security patches more easily
than vice versa.

## Lesson 0n: Duplicate PR patterns indicate automation opportunities (2026-04-03)

**Pattern:** Multiple similar fixes across repos (ANSI stripping, fnmatch
optimization, TTY degradation) suggest repetitive automation. **Rule:** Consider
creating shared libraries or common patterns to reduce duplicate PR creation.
Track duplicate patterns to identify consolidation opportunities.

## Lesson 0o: GitHub MCP API cannot auto-merge some repos (2026-04-03)

**Pattern:** `mcp4_merge_pull_request` fails with "Pull Request is not
mergeable" even when PR has no conflicts and all checks pass. PRs return
`merge_commit_sha: null` and `mergeable: null` in API responses. **Root cause:**
Repository settings or branch protection rules may require manual merge approval
or lack auto-merge configuration for MCP tools. **Rule:** When automated merge
via MCP tools fails, verify repo settings: (1) Enable auto-merge in repository
settings, (2) Check branch protection rules for merge restrictions, (3) Verify
MCP token has sufficient permissions. For security PRs that pass all gates,
document approval status and provide manual merge instructions via GitHub UI.

## Lesson 0q: Inventory regex can miss Jules PRs with “fix/” branches (2026-04-11)

**Pattern:** A Jules PR uses branch
`fix/github-actions-checkout-version-<taskid>` and title `ci(actions): …` with
**no** Bolt/Sentinel/Palette emoji — branch regex may **exclude** it even though
the **body** contains `PR created automatically by Jules` and a
`jules.google.com` task link. **Rule:** Treat PR body/footer as a first-class
automation signal when building `tasks/pr-inventory.md` (not only branch/title).
Optionally match `jules\.google\.com/task/` in `gh pr view --json body`.

## Lesson 0p: Jules zero-diff QA PRs pollute PR list (2026-04-03)

**Pattern:** Automated Jules Daily QA creates PRs with `changedFiles: 0` when QA
passes but no code changes are needed. PR body contains valuable findings, but
empty diff adds noise to PR list. **Rule:** Close zero-diff QA PRs immediately
with comment acknowledging findings. If QA findings are valuable, extract them
to `tasks/lessons.md` or session reports. Configure Jules to skip PR creation
when `git diff --stat` shows no changes.

## Lesson 0t: Broken pre-existing tests on `main` create a queue jam (2026-04-25)

**Pattern:** On `email-security-pipeline`, the `pytest` job on `main` has been
failing with collection-time `SyntaxError`s in unrelated test files
(`tests/test_alert_error_redaction.py`, `tests/test_error_recovery.py`,
`tests/test_media_analyzer_error_handling.py`, etc.) since 2026-04-23. Every
open PR's CI rollup goes UNSTABLE because the same broken collection step runs
against the merge base — even tests-only PRs and pure UX changes that don't
touch the broken files at all. **Rule:** When a required CI job fails for a
reason that lives **on `main`** rather than in the PR's diff, the agent must
**defer all merges** in that repo and surface a single top-priority escalation:
"fix the test infra on `main`." Do **not** merge security-sensitive PRs
(especially in a security pipeline) over a broken pytest gate, even if the PR's
own changes are unrelated. The fix must land on `main` (via a maintenance PR or
direct push by a human) before any in-flight PRs in that repo can be evaluated
end-to-end. **Detection heuristic:** If 4+ PRs in the same repo show the same
failing required check **and** the same job has failed on `main` since at least
one merge ago, treat it as infra failure on `main` rather than a per-PR failure.

## Lesson 0u: A single in-scope PR can fix the CI infra it depends on — merge it first, then sync siblings (2026-04-25)

**Pattern:** `Seatek_Analysis`'s `validate` workflow had been failing because
`Series_27/Analysis/requirements.txt` pinned `pandas>=3.0.2`, which requires
Python 3.11, while the workflow used `python-version: "3.10"`. PR `#155` (a Bolt
list-comprehension change) also included a one-line requirements pin
(`pandas>=1.3.0,<3.0.0`) and bumped CI to Python 3.11. Merging it first
unblocked validate for the entire repo. **Rule:** When triaging a repo whose CI
is infra-broken, **scan inventory PRs for an in-scope diff that fixes the
infra** (e.g. requirements pin, workflow file edit, action version bump) before
deferring the whole repo. If found:

1. Merge that PR first (security-and-infra ordering).
2. After it merges, call `gh api -X PUT repos/$REPO/pulls/$PR/update-branch` on
   each sibling PR to re-run their checks against the fixed workflow.
3. Re-evaluate mergeability and proceed with the normal merge order.
   **Caveats:** `update-branch` returns HTTP 422 if the PR has a real merge
   conflict (not just stale base). Treat that as DIRTY and defer for human
   rebase. Some PRs that pass the new validate may also become **zero-diff**
   once synced (their change was already on `main`); close those per Lesson 0b.

## Lesson 0v: Closing duplicate Sentinel/Palette/Bolt PRs benefits from explicit superset accounting (2026-04-25)

**Pattern:** Across `personal-config` and `ctrld-sync`, multiple
Sentinel/Palette/Bolt PRs landed within 24 hours of each other proposing the
**same fix** at different scopes. Examples: <!-- pragma: allowlist secret -->

- `personal-config` `#823` (4 files, includes `clean/system.sh`) ⊃ `#815` (4
  files, includes only `.jules/sentinel.md` journal)
  <!-- pragma: allowlist secret -->
- `personal-config` `#822` (3 files including `view_logs.sh` + `setup.sh`) ⊃
  `#810` (2 files) <!-- pragma: allowlist secret -->
- `ctrld-sync` `#742` (4 files including `tests/test_ux.py`) ⊃ `#736` (2 files)
- `ctrld-sync` `#740` (3 files including `pr_payload.json` artifact) ⊃ `#735` (2
  files) **Rule:** When closing as duplicate, the comment must:

1. Name the canonical PR explicitly with file overlap delta (e.g. "#823 covers
   `clean/system.sh` additionally").
2. Note any unique content in the closed PR that does **not** carry forward
   (typically only the journal entry under `.jules/`), so a reviewer can decide
   whether to extract it.
3. Cite Lesson 0n so the consolidation rationale is traceable.

## Lesson 0x: SyntaxError at line 1 of a "perf" PR can mean the file was committed as a JSON-encoded blob (2026-04-26)

**Pattern:** `email-security-pipeline` `main` had been failing pytest with
`SyntaxError: unexpected character after line continuation character` at
`src/modules/media_analyzer.py:1` since 2026-04-23. Inspecting the file showed
line 1 starting with literal `\n`/`\"` escape sequences — the entire ~28KB file
was committed as a JSON string instead of source code, by an automation agent's
PR (#693) that intended to add a perf optimization. **Rule:** When a CI infra
failure is a `SyntaxError` at the very first line of a file, treat "the file is
a stringified blob" as a top hypothesis. Verify by running
`codecs.decode(open(file).read(), 'unicode_escape')` and checking whether the
result compiles. **Important:** even when the decode produces valid Python, the
_content_ may be a regression — the bot agent may have round-tripped the file
through an LLM that lost detail (in this case, ~547 lines of validated zip/tar
inspection logic disappeared). The safest fix is **revert to the parent
commit**, not re-commit the decoded blob. File a separate clean PR for the perf
optimization that was intended. **Detection cost:** This single broken file
blocked **every** open PR's pytest gate in the entire repo for >2 days because
the file is transitively imported by every test that touches
`src.modules.alert_system`. Catching this earlier (e.g. a pre-commit hook that
runs `python -m py_compile` on all changed `.py` files) would be cheap
insurance.

## Lesson 0de: "Cleanup" PRs that truncate append-only journal files are an integrity regression (2026-04-26)

**Pattern:** Several Bolt/Sentinel automation PRs replaced (rather than appended
to) `.jules/bolt.md` / `.jules/sentinel.md` / `.jules/palette.md`. Examples:

- `personal-config#820` truncated `.jules/bolt.md` from 131 lines to 11 while
  applying a valid 3-file `.py` perf optimization.
  <!-- pragma: allowlist secret -->
- Several other PRs in this session show similar full-rewrite patterns on these
  journal files. **Rule:** Treat `.jules/*.md`, `CHANGELOG.md`,
  `.jules/sentinel.md`, and any other append-only journal as
  **content-protected** during salvage. When salvaging a PR that touches one of
  these files, take only the new appended entry and merge it on top of `main`'s
  current journal — never copy the journal version from the PR wholesale. If the
  salvage tool of choice is `git checkout pr_branch -- file`, do **not** apply
  that to a journal file; instead, extract the new entry with `diff` or by
  reading the PR diff and append it programmatically.

## Lesson 0dt: Salvageable test contributions need API adaptation, not a wholesale checkout (2026-04-26)

**Pattern:** `personal-config#816` proposed to refactor `run_gh` to take an args
list and added `tests/test_vulnerability_fix.py` to lock in the change. By the
time we reviewed the PR, the security refactor had already landed on main via
`#788`, but with a _different_ `run_gh` signature than #816 assumed. A wholesale
`git checkout pr816 -- tests/test_vulnerability_fix.py` produced a test file
that asserted `cmd[0] == "gh"` against a list whose first element was `"pr"` —
failing because the test was written for a signature that never landed.

<!-- pragma: allowlist secret --> **Rule:** When salvaging a test from a

deferred PR:

1. Re-read the test against the current implementation on `main` to confirm
   signatures and call sites match.
2. Adapt the test to the actual API on `main`, not to the API the original PR
   proposed.
3. Use an `ast`-based isolated loader (or `runpy.run_path` with controlled
   globals) when the target script has module-level side effects that you don't
   want to execute at test time.
4. Strengthen the test with at least one defense-in-depth assertion (e.g. for
   #826, the original asserted only "no `shell=True`"; the salvage added
   "`_load_gh_token_env` must not call `subprocess.{run,Popen}`" so a future
   shell-out via env-loader is also caught).

## Lesson 0aa: `gh api PUT .../update-branch` HTTP 422 means a real conflict, not stale base (2026-04-26)

**Pattern:** When attempting to sync deferred PR branches with main,
`gh api -X PUT repos/$REPO/pulls/$PR/update-branch` returned
`HTTP 422: merge conflict between base and head` for several PRs (e.g.
`Seatek_Analysis#156`, `ctrld-sync#737`). This is **not** the same as
`422: There are no new commits on the base branch.` (which is benign). **Rule:**
Distinguish the two `422` responses by the `message` body:

- `"There are no new commits on the base branch."` → benign; the branch is
  already current.
- `"merge conflict between base and head"` → real content conflict that GitHub's
  auto-merge cannot resolve. The salvage path is to **apply just the unique
  files** from the PR onto a fresh branch from main
  (`git checkout pr_branch -- path/to/file`) rather than try to rebase the
  original branch interactively.

## Lesson 0bb: For a public security pipeline, never bypass a broken-on-main test gate even for "unrelated" PRs (2026-04-26)

**Pattern:** During the 2026-04-25 session, six `email-security-pipeline` PRs
(some CRITICAL/MEDIUM Sentinel fixes) carried CI rollups of `MERGEABLE/UNSTABLE`
because pytest was failing on `main` for an unrelated reason (the corrupted
`media_analyzer.py` from Lesson 0x). The runbook permits "Failing due to
flaky/unrelated test → note and proceed with caution," but for a security
pipeline the agent erred on the side of "do not bypass" and deferred all six.
**Rule:** Codify the email-security-pipeline (and any future security-classified
repo) as **never-bypass** when pytest is red on main. Surface the infra failure
as the top escalation, fix it (Lesson 0x salvage workflow), then re-evaluate the
queue. The cost of a slightly delayed merge is much lower than the cost of
accidentally merging a CRITICAL bypass behind a green-by-omission gate.

## Lesson 0cc: Burst squash merges can DIRTY overlapping automation branches immediately (2026-05-03)

**Pattern:** On `personal-config`, sequential squash merges of ~20 small CLEAN
Bolt/Jules/Sentinel PRs within minutes flipped sibling PRs touching shared
hotspots (`run_merges.py`, `parse_inventory.py`, Palette prompts, Jules QA
shells) from **MERGEABLE/CLEAN** to **CONFLICTING** mid-queue — even though each
PR passed CI in isolation. **Rule:** After high-volume merges in one repo,
assume mergeability metadata is stale until refreshed; batch merges must pause
when GitHub reports **merge conflicts** or `update-branch` returns HTTP **422**
(`merge conflict between base and head`). Prefer finishing **one semantic lane**
(e.g. all concurrent Bolt PR-fetch changes) before opening adjacent lanes, or
accept that the tail requires human conflict resolution (**no force-push**).

## Lesson 0cd: Delegated salvage summaries must be verified against live PR state (2026-05-06)

**Pattern:** Multi-agent salvage summaries can drift from current GitHub reality
(e.g., replaying old Phase 2 counts or reporting CLEAN while checks have flipped
UNSTABLE). **Rule:** Before making merge/close decisions from delegated output,
run a direct `gh pr view/list` verification sweep on the load-bearing PRs
(state, mergeability, failing checks, recent comments). Treat sub-agent output
as a report, not ground truth.

## Lesson 0dd: Identical twin PRs can pass the same CI with the same file list (2026-05-09)

**Pattern:** Two open PRs (**#785** / **#786** on `email-security-pipeline`)
changed the same three paths (`src/utils/caching.py`, `tests/test_caching.py`,
`.jules/bolt.md`) with the same intent; both showed green rollups. **Rule:**
Before merging either, diff **titles + head SHAs + file lists** side-by-side.
Pick one canonical PR (prefer the lower number if identical), squash-merge it,
then **close** the twin as duplicate—do not leave both open to drift.

## Lesson 0w: Branch-protection introspection may be denied by personal-account tokens (2026-04-25) <!-- pragma: allowlist secret -->

**Pattern:** `gh api repos/$REPO/branches/main/protection` returns
`HTTP 403: Resource not accessible by [REDACTED] access token` for all five
repos in this config when authenticated as the personal owner. This does **not**
indicate misconfigured branch protection — it just means the token scope can't
read the protection record. <!-- pragma: allowlist secret --> **Rule:** Treat
403 on the protection-read endpoint as benign for personal repos. Verify
branch-protection behavior via merge attempts instead (`gh pr merge` will fail
with a clear error if rules block the merge). Keep the preflight gate looking at
`gh auth status` and `gh repo view` rather than the protection endpoint.

<!-- pragma: allowlist secret -->

## Lesson 0gg: v2 salvage branches can pick up whole-repo scope creep (2026-05-23)

**Pattern:** Draft salvages `#1020` and `#1021` on `personal-config` each showed
~402 changed files and ~42k insertions despite titles claiming tests-only or
adguard-only intent. Likely caused by branching from a stale/conflicted base
instead of a fresh shallow `main` clone. **Rule:** Phase 2 must clone to
`/tmp/salvage-<slug>-<date>/` with `git clone --depth=1`, create the branch from
`origin/main`, and stage **only** the paths listed in the salvage plan. Before
`git push`, assert `git diff --stat origin/main` touches ≤10 files (or abort).
Close scope-creep PRs with a comment rather than attempting `update-branch`.
**Detection cost:** Low — `gh pr view --json changedFiles` > 20 on a
“tests-only” salvage is an immediate red flag.

## Lesson 0cc: Salvage batch2 branches go DIRTY after every personal-config merge wave (2026-05-20)

**Pattern:** Eleven `cursor-agent/salvage-personal-config-*-pc-batch2` PRs were
opened 2026-05-19; after merges #989, #994, #999, #1002, and #1004 landed on
`main`, every `gh api …/update-branch` returned HTTP 422
(`merge conflict between base and head`). Sentinel fixes in #986–#988 overlapped
the same mole core paths. **Rule:** After a merge burst on `personal-config`,
treat batch salvage branches as stale. Rebuild with
`git checkout -b cursor-agent/salvage-<repo>-<old_pr>-v2-<date> origin/main`,
`git checkout origin/<old-salvage-branch> -- <minimal paths>`, verify, push,
open a **new draft** PR, then close conflicted salvages. Do not rely on GitHub
“Update branch” for batch2 tails. **Detection cost:** Low — one `update-branch`
422 on any batch2 PR implies the whole batch needs v2.

## Lesson 0dg: Sentinel PRs with scratch `.diff` siblings should lose to a clean branch (2026-05-23)

**Pattern:** `series_correction_project_updated#55` carried nine files including
`fix_*.diff`, `patch.diff`, and `batch_correction.py.orig` beside the real fix;
`#58` changed only `batch_correction.py`, `processor.py`, and tests with the
same security intent. **Rule:** When two Sentinel/Bolt PRs target the same CWE,
prefer the branch with **no** scratch patch artifacts. Close the noisy PR with
an explicit supersession link before merging the clean one.

## Lesson 0dh: `greeting` and `benchmark` failures are infra lanes, not always PR regressions (2026-05-23)

**Pattern:** `email-security-pipeline#897` failed only `greeting` while twin
`#896` was identical and green. `ctrld-sync#837`/`#835` failed only `benchmark`
with otherwise mergeable security/perf diffs. **Rule:** Diff twin PRs before
blaming application code. Close the worse twin when file lists match. Escalate
benchmark/greeting lanes repo-wide when multiple unrelated PRs share the same
single failing check.

## Lesson 0di: CWE-94 workflow comments live in YAML preamble, not inside `github-script` step text (2026-05-24)

**Pattern:** After merging #1037,
`test_copilot_setup_steps_cwe94.test_security_comment_documents_cwe94` failed
because it asserted `CWE-94` inside the extracted Development Partner step
block; the fix documents CWE-94 in a `# SECURITY:` comment immediately above the
step. **Rule:** Static workflow tests should scan the workflow preamble before
the step marker, or parse the full workflow file, when asserting on security
documentation comments.

## Lesson 0dj: Action SHA pin hunks can strip YAML preamble SECURITY blocks (2026-05-25)

**Pattern:** Salvage PR #1050 pinned `setup-python` / `github-script` SHAs and
removed the three-line `# SECURITY` / `CWE-94` preamble above
`Development Partner Session`, while duplicating CWE-94 text inside the
`script:` block. `test_security_comment_documents_cwe94` failed until the
preamble block was restored. **Rule:** When auto-fixing or reviewing workflow
PRs that pin action SHAs, diff the full step preamble—not only the `uses:`
line—and preserve SECURITY/CWE comments required by regression tests.

## Lesson 0df: A salvage agent given a "no local working-tree manipulation" rule will still `git checkout` if its prompt mentions cherry-picking commits (2026-05-09)

**Pattern:** Item 4A of the 2026-05-09 orchestration plan briefed a `pair` agent
with "no local working-tree manipulation" plus "create a salvage branch from
`origin/main` and cherry-pick the canonical PR's commits." The agent interpreted
that as licence to `git checkout <pr-branch>` in the working repo to read the
commit list, switching the local tree off `main` for the rest of the session.
Untracked-only documents (`docs/plans/`, `docs/reviews/`) were destroyed by the
branch switch, and 51 unrelated files ended up staged on the bolt branch.
**Rule:** Brief salvage agents to do **all** branch work in a `git clone` under
`/tmp/<slug>-<date>/`, never in the working repo. The brief must call this out
positively ("clone the repo into `/tmp/…` first; never `git checkout`,
`git switch`, or `git fetch <ref>:<ref>` inside the active workspace") rather
than relying on an unspecific "no working-tree manipulation" guard. Commit
important orchestration documents (plans, reviews, handoffs) to `main`
**before** dispatching any salvage agent so an unintended `git checkout` cannot
erase them. **Detection cost:** Medium — surfaces only after the next session
runs `git status` and finds an unexpected branch with staged churn. Recovery
requires a careful unstage + stash + branch switch + reconstruction from
surviving artifacts.

## Lesson 0dl: Bolt perf PRs may skip GitHub Actions test workflows (2026-05-26)

**Pattern:** `ctrld-sync#849` and `email-security-pipeline#936` showed only
advisory checks (CodeScene, Snyk, Devin) — no `pytest`/`ruff`/`test` workflow in
the PR check rollup. **Rule:** Before merging logic-changing Bolt PRs, run the
repo's local test suite on the PR branch (`uv run pytest` /
`python3 -m pytest`). Do not rely on advisory-only green checks for application
code.

## Lesson 0dm: Sequential doc-artifact merges conflict on shared task files (2026-05-26)

**Pattern:** Merging personal-config #1064 (review session docs) then #1066
(salvage session docs) caused conflicts in `tasks/pr-inventory.md`,
`tasks/pr-triage.md`, and `tasks/pr-review-2026-05-25.md`. **Rule:** When two
session-doc PRs touch the same task files, merge the older session first, then
resolve conflicts on the newer branch keeping session-specific content (or
consolidate into one PR).

## Lesson 0dn: Competing `load_config` security PRs — prefer containment over substring denylist (2026-05-27)

**Pattern:** Jules #80 added a `..` substring check; Cursor #78 (draft) used
`os.path.commonpath` containment plus a test `chdir` fix. Both had green
advisory CI. **Rule:** When two automation PRs fix the same CWE-22 surface,
compare mechanisms; prefer resolved-path containment. Close the weaker duplicate
with a link to the keeper. Mark draft security PRs `ready` before merge when
checks are green.

## Lesson 0do: Jules QA Black PRs may follow perf merges on hot files (2026-05-27)

**Pattern:** After merging ESP #943, Jules opened #944 with Black-only changes
to `setup_wizard.py` (long-line fix class previously deferred as #937).
**Rule:** Treat post-merge Jules style PRs as in-scope when diff is
formatting-only, security scans pass, and pytest is green — merge before opening
the next salvage on the same file.

## Lesson 0dk: Salvage drafts must be built _after_ the Phase 1 merge burst, not in parallel (2026-05-25)

**Pattern:** During the 17:00 salvage cron, ESP salvages #930/#931 were pushed
from `main` snapshots taken before #917/#927/#929 merged. GitHub immediately
marked both drafts `DIRTY`/`CONFLICTING` even though CI had not yet run.
**Rule:** Order operations: (1) merge all CLEAN PRs in a repo, (2)
`git fetch origin main`, (3) build salvage branches with `-v2` suffix, (4) close
stale salvage drafts. Never open salvage PRs until the repo's merge burst for
that session is complete. **Detection cost:** Low — `mergeStateStatus: DIRTY` on
a draft opened seconds after creation.

## Lesson 0dp: Close obsolete salvage when main already contains the perf intent (2026-05-27)

**Pattern:** `#1065` (scratch_triage modularization v2) conflicted and removed
`ThreadPoolExecutor` already merged via `#1076`. **Rule:** Before opening v4 for
a conflicting salvage, `git diff origin/main...salvage-head -- <intent-files>`;
if the salvage **removes** capabilities already on `main`, close as superseded —
do not rebuild.

## Lesson 0dq: v4 TOCTOU salvage must not cherry-pick Palette/setup_wizard churn (2026-05-27)

**Pattern:** v3 `#939` mixed TOCTOU fixes with provider-menu string downgrades
and `re.sub` lambda churn; patch would not apply to current `main`. **Rule:**
Re-implement security hunks manually on fresh `main` or extract only
`_set_secure_permissions` / inode-verify blocks; never `git apply` a stale
multi-intent bot diff.

## Lesson 0dl: Salvage branches must contain only intent files — never whole-bot diffs (2026-05-26)

**Pattern:** v2 salvage branches for ESP (#932/#933) included `.jules/*.md`
deletions, `CHANGELOG` churn, and large unrelated edits to `spam_analyzer.py` /
`email_parser.py` from a stale bot base. Seatek v2 branches similarly pulled
workflow automation file regressions. **Rule:** When rebuilding (v3+),
`git checkout salvage -- <intent-files-only>` from a fresh `origin/main` branch.
For TOCTOU use only `app_runner.py` + `setup_wizard.py`; for IMAP perf use only
`email_ingestion.py` + its tests; for R tests use only `tests/testthat/*`
targets. **Detection cost:** Low — `gh pr diff` file count ≫ original bot PR
file list.

## Lesson 0dr: ctrld-sync benchmark job is CI-flaky — not a merge blocker for unrelated changes (2026-05-28)

**Pattern:** Palette #854 (one-line emoji) and Sentinel #852 (security refactor)
both failed `benchmark` with 1.5–2× perf alerts against prior runner baselines.
All application checks (`test`, `ruff`, `bandit`, `mypy`) passed. **Rule:**
Treat ctrld-sync benchmark failures as infrastructure variance unless the PR
modifies benchmarked hot paths. Merge when substantive checks are green; note
benchmark flake in merge body.

## Lesson 0ds: Duplicate Jules Daily QA branches — diff before triage (2026-05-28)

**Pattern:** ESP #952 and #953 had identical diffs on different branch names;
#952 had a transient `greeting` fail while #953 was fully green. **Rule:**
`diff <(gh pr diff A) <(gh pr diff B)` on same-day Jules QA pairs; merge the
all-green branch, close the duplicate with a link.

## Lesson 0y: Third-party bandit actions can block SHA-only repos (2026-05-29)

**Pattern:** ESP #957 pinned `actions/checkout` in
`.github/workflows/bandit.yml`, but the `shundor/python-bandit-scan` composite
still referenced unpinned `actions/upload-artifact@main` and
`github/codeql-action/upload-sarif@v3`, so the bandit job failed org policy
anyway. **Rule:** Before deferring a “workflow pin” PR as complete, read the
**failed job log** for nested unpinned actions. Fix by replacing the composite
with inline bandit + fully pinned SARIF upload steps, or escalate for a
maintained fork — pinning only checkout is insufficient. **Detection cost:** Low
— one `gh run view --log-failed` on the bandit job.

## Lesson 0z: “Workflow consolidation” PRs can unpin SHAs (2026-05-31)

**Pattern:** ESP #966 replaced full commit SHAs with mutable tags
(`actions/github-script@v9.0.0`) and `upload-sarif@codeql-bundle-v2.25.5`,
causing bandit to fail with “actions must be pinned to a full-length commit
SHA.” **Rule:** Treat tag-based workflow edits as **merge blockers** in SHA-only
repos. Required fixes must pin **every** action reference (including SARIF
upload), never downgrade SHA → tag. Close or rewrite the PR before re-triage.
**Related:** Lesson 0y (nested unpinned actions inside composites). **Detection
cost:** Low — bandit workflow fails before pytest on workflow-only diffs.

## Lesson 0cg: Jules Palette branches can duplicate with session-id suffix (2026-06-08)

**Pattern:** ESP #1049 (`ux/fix-eof-crash`) and #1050
(`ux/fix-eof-crash-<sessionId>`) had byte-identical diffs opened minutes apart.
**Rule:** `diff <(gh pr diff A) <(gh pr diff B)` on same-title Palette PRs; keep
the session-id branch (newer Jules run), close the shorter branch with a linked
explanation. Merge before attempting sibling Bolt PRs in the same repo to avoid
Lesson 0c retries.

## Lesson 0cf: Jules agentic QA zero-diff PRs are routine closures (2026-06-07)

**Pattern:** personal-config #1183 opened same day with title "chore: automated
agentic QA review", `changedFiles == 0`, CI fully green — Jules completed QA
with no pending code changes after prior session merges. **Rule:** Close
immediately with Lesson 0b comment; do not squash-merge empty commits. Expect
one per repo per Jules daily QA cycle when `main` is already healthy.

## Lesson 0cg: Fleet-wide conflict clearance — salvage focuses on hygiene (2026-06-08)

**Pattern:** Evening salvage cron found zero `CONFLICTING` / `DIRTY` bot PRs
across all six configured repos; work shifted to duplicate closure (#1053),
zero-diff QA (#1189), and superseded doc drafts (#1185). **Rule:** When the
conflict queue is empty, Phase 2 should still run: close semantic duplicates,
zero-diff Jules QA, and superseded salvage-doc PRs; route CLEAN code PRs to
Phase 1 rather than merging from salvage. **Detection cost:** Low —
`gh pr list --json mergeable,mergeStateStatus` per repo.

## Lesson 0ce: T1 security merges with CodeScene-only failure (2026-06-06)

**Pattern:** ESP #1008 had `mergeStateStatus: UNSTABLE` solely because CodeScene
Code Health Review failed; bandit, CodeQL, pytest, Snyk, and GitGuardian were
all green. **Rule:** CodeScene is advisory unless branch protection marks it
required. For T1 security salvages, merge when the full security test suite
passes and the diff addresses the vulnerability — do not defer solely on
CodeScene delta. **Contrast:** Defer perf salvages (#261, #227) where CodeScene
is the only failure and the change is not security-critical.

## Lesson 0cd: Salvage workflow-heavy Bolt PRs with minimal file set (2026-06-01)

**Pattern:** Seatek #237 touched eight workflow YAML files plus
`code_health_scanner.py`; rebasing the full branch risked unrelated CI churn.
**Rule:** When the substantive fix is a single script, salvage **only that
file** unless workflow changes are required for the optimization to work.
Document omitted paths in the salvage PR body. **Detection cost:** Low — inspect
`gh pr view --json files` before checkout.

## Lesson 0cg: Salvage PRs go DIRTY when main refactors overlap intent files (2026-06-09)

**Pattern:** Hydrograph #227 was MERGEABLE with CodeScene-only failure on
2026-06-07; by 2026-06-09 it was `CONFLICTING`/`DIRTY` because `main` gained
`_create_chart_metadata` / `_save_generated_chart` while the salvage branch
inlined/reverted that refactor in `app.py`. **Rule:** Before `update-branch` on
a deferred salvage, diff `main` against salvage intent files. If `main` already
refactored the same surface, rebuild v2 from `main` with **intent files only** —
never fight an app-level refactor in the salvage branch. **Detection cost:** Low
— `mergeStateStatus: DIRTY` on a PR that was previously MERGEABLE.

## Lesson 0ci: Salvage test checkout must append, not replace (2026-06-11)

**Pattern:** series_correction #109 salvage initially ran
`git checkout pr-109 -- scripts/tests/test_processor.py`, replacing 58 lines of
existing `detect_outliers` tests with 22 lines from the Jules branch. **Rule:**
Before committing a test-file salvage, compare line counts: `main` vs PR vs
staged. If staged file is **shorter** than `main`, abort and **append** the new
test functions instead of wholesale checkout (Lesson 0dt). **Detection cost:**
Low — `git diff --stat` net-negative on a test file is a tripwire.

- **Bash Eval Injection in Subshells**: When running traps inside a subshell
  instead of `eval`, the trap must explicitly use `$BASHPID` instead of `$$` if
  it wants to signal itself properly, because `$$` refers to the parent process.
  Also, ensure the subshell's trap explicitly handles signal propagation (e.g.
  `trap - INT; kill -INT $BASHPID`) so that the subshell terminates correctly,
  and then the parent script's wait mechanism triggers properly (WCE).

## Lesson 0ch: Bolt sum([list]) materialization causes real benchmark regression (2026-06-10)

**Pattern:** ctrld-sync #881 replaced `sum(genexpr)` with `sum([list comp])` in
four hot paths. All functional checks passed but benchmark reported ~1.5–2×
slowdown — list materialization allocates before summing. **Rule:** When a Bolt
PR converts generators to list comprehensions inside `sum()`, treat benchmark
failure as substantive unless the hot path is cold. Prefer keeping generator
expressions or use `math.fsum` on an iterator. Do not apply Lesson 0dr flake
waiver when the PR touches benchmarked summation loops. **Detection cost:** Low
— `benchmark=FAILURE` on a Bolt diff that adds `[` inside `sum(`.

## Lesson 0ci: CodeScene PASS does not override security control removal (2026-06-10)

**Pattern:** Seatek #261 salvage draft achieved CodeScene SUCCESS after five
sessions of advisory failure, but the diff removed `read_file_safe`,
`MAX_FILE_SIZE`, and associated security tests. **Rule:** Gate 2 (security)
blocks merge even when CodeScene is green. Before recommending human merge on a
perf salvage, verify intent files did not drop path-traversal, size-limit, or
auth helpers present on `main`. **Contrast:** Lesson 0ce (merge T1 security when
CodeScene-only fail) — opposite direction; security wins over advisory green.
**Detection cost:** Low — `gh pr diff` shows deletion of `read_file_safe` or
`MAX_FILE_SIZE`.

## Lesson 0cj: Duplicate same-day Bolt hoists — close the noisier branch (2026-06-12)

**Pattern:** personal-config #1226 and #1227 both hoisted `_CATEGORIES` in
`categorize_ready.py` on the same day. #1226 added `.jules/bolt.md` churn; #1227
was the cleaner intent-only diff with matching test updates. **Rule:** When two
Bolt PRs target the same refactor, compare `changedFiles` and diff noise
(session docs, `.jules/*`, scratch fixtures). Close the duplicate with a comment
linking the winner; squash-merge the minimal diff. Do not merge both.
**Detection cost:** Low — identical titles or overlapping `categorize_ready.py`
/ test file paths in inventory.

## Lesson 0ck: Truncated automation common module blocks unrelated PR CI (2026-06-13)

**Pattern:** personal-config `main` lost `DAILY_WORKFLOW_NAME` in
`repository_automation_common.py`, causing `ImportError` in
`test_repository_automation_tasks` and failing `Run All Tests` on unrelated
Bolt/Palette PRs (#1234, #1235). **Rule:** When multiple green MERGEABLE PRs
share the same failing test import, check `main` first for infra breakage before
deferring each PR individually. Open or escalate a T0 infra-fix draft (#1231
pattern) before Phase 1 merge burst. **Detection cost:** Low — identical
`ImportError` across PR branches with no overlapping changed files.

## Lesson 0cl: Stale Seatek Bolt branches can delete merged tests (2026-06-13)

**Pattern:** Seatek #278 and #282 were `DIRTY` but a full
`git diff main..branch --stat` showed net deletion of six `tests/testthat/*`
files merged on `main` since 2026-06-11. **Rule:** Before salvaging a `DIRTY` R
perf PR, run `git diff main..branch --stat` on `tests/`. If net-negative on test
files, close as stale — do not cherry-pick the branch wholesale. **Detection
cost:** Low — one `git diff --stat` per deferred Seatek PR.

## Lesson 0cm: Duplicate T0 infra-fix drafts — keep newest (2026-06-14)

**Pattern:** personal-config #1231 and #1240 both restored truncated
`repository_automation_common.py` as draft infra-fix PRs opened a day apart.
**Rule:** When multiple draft infra-fix PRs target the same broken `main` file,
close the older draft and escalate the newest for human merge. Do not leave
parallel T0 drafts open. **Detection cost:** Low — same title prefix and
identical primary file path in inventory.

## Lesson 0cn: Sibling Bolt merge makes follow-up DIRTY (2026-06-14)

**Pattern:** ctrld #892 merged `_parse_and_cache_response` refactor; sibling
#898 (Content-Type unroll) went `DIRTY` and picked up unrelated
`repository_automation_common.py` diff noise. **Rule:** After a sibling Bolt PR
merges, rebuild follow-up optimizations from current `main` with intent files
only — do not rebase the original DIRTY branch. **Detection cost:** Low —
`mergeStateStatus: DIRTY` on a PR whose title matches a recently merged sibling
optimization.

## Lesson 0cp: Combine DIRTY code + journal salvage; drop duplicate journal entries (2026-06-16)

**Pattern:** ctrld #901 (main.py refactor) and #904 (anti-micro journal) both went `DIRTY` after the same merge burst (#905/#906/#902). #901's journal entry duplicated content already on `main` from an earlier merge. **Rule:** When salvaging sibling DIRTY PRs from the same burst, open one draft branch from current `main`: take production code from the code PR, append-only journal from the doc PR, and skip journal lines already present on `main`. **Detection cost:** Low — two open PRs on the same repo with overlapping `.jules/bolt.md` paths and `DIRTY` status after a burst merge.

## Lesson 0cr: Salvage one-line fixes from DIRTY Jules PRs; omit CodeScene refactors (2026-06-19)

**Pattern:** pc #1281 bundled a one-line podcast error-path `html_section()` a11y fix with CodeScene-driven `_parse_linear_focus_node` inlining that conflicted with `main`. **Rule:** When a DIRTY bot PR's stated intent is a small functional fix but the diff includes unrelated complexity refactors, salvage only the functional lines onto a fresh `main` branch. **Detection cost:** Low — `gh pr diff --stat` shows large churn in unrelated functions alongside a one-line stated fix in the PR title.
## Lesson 0db: Large Phase 1 merge bursts predictably cascade DIRTY test PRs (2026-06-30)

**Pattern:** After squash-merging 22 personal-config PRs in one session, nine sibling test PRs flipped to `DIRTY` (all touching overlapping `tests/*` files). CI was green on each before the burst; conflicts appeared only at merge time. **Rule:** When planning a merge burst on repos with dense Jules test PR clusters, pre-identify file-path overlap and either (a) merge the largest test-file PR first then immediately salvage DIRTY siblings from current `main`, or (b) batch-salvage before closing originals. Do not attempt `update-branch` retries indefinitely — switch to salvage-from-main after one 422 conflict response. **Detection cost:** Low — multiple open PRs sharing the same `tests/test_*.py` basename in inventory.

## Lesson 0dc: Salvage PRs can themselves go DIRTY — verify value still missing on main (2026-07-02)

**Pattern:** esp #1202 was a prior-session salvage draft that became `DIRTY` while `main` had already absorbed the functional change (`REDACTED_URL_PATTERN` at class level). **Rule:** Before re-salvaging a conflicted salvage PR, diff its intent against current `main`. If the change is already present (even with a different implementation), close as superseded — do not open another draft. **Detection cost:** Low — `git diff main..branch -- <intent_file>` or grep for the stated symbol on `main`.

## Lesson 0dd: Jules UX PRs with refactor churn — salvage isatty guards only (2026-07-02)

**Pattern:** ctrld #965 mixed valuable `stderr.isatty()` guards with 400+ lines of unrelated refactors (nested functions, folder parsing moves), causing `DIRTY` + CodeScene failure. **Rule:** For Palette/Jules UX PRs where the title states an isatty/ANSI guard, salvage only those guard lines and matching tests onto fresh `main`; discard bundled refactors. **Detection cost:** Low — PR title mentions isatty/ANSI while `git diff --stat` shows >100 lines outside `countdown_timer`/`render_progress_bar`.

## Lesson 0de: Copilot workflow PRs with session.db artifacts fail security gates (2026-07-03)

**Pattern:** pc #1470 bundled valuable workflow consolidation with `.adk/session.db` binaries, `all.patch`, and `tasks/todo.md` text that triggered Gitleaks `personal-config-generic-secret`. **Rule:** Close PRs that mix CI/workflow changes with session DB binaries or journal false-positives; if the workflow work is still wanted, open a focused PR touching only `.github/workflows/` + docs. **Detection cost:** Low — `git diff --name-only` includes `*.session.db` or `.adk/` paths alongside workflow files.

## Lesson 0df: Exclude trust-boundary files from Bolt salvage (2026-07-03)

**Pattern:** pc #1466 mixed a legitimate `system_metrics.sh` awk optimization with `get_repo_vars.sh` (GitHub API probe) and `gemini-review.yml` secret-line removal. **Rule:** When salvaging DIRTY Bolt/Jules perf PRs, take only the stated performance file + journal entry; drop API probe scripts and workflow credential edits. **Detection cost:** Low — salvage diff includes new shell scripts calling `gh api` or workflow files removing `secrets.*` lines.

## Add testing for missing edge cases
When testing parsing/formatting logic, always consider unexpected data types, out of bound values and common malformed shapes.
