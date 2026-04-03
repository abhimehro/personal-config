# Lessons Learned

## Lesson 0: Multi-repo automated PR merges need sequential re-validation

**Pattern:** After squash-merging one automation PR, sibling PRs from the same bot often become **CONFLICTING** with `main`.
**Rule:** Re-run mergeability after each merge; merge `origin/main` into the PR branch and resolve conflicts with ordinary commits (never force-push). Use `GH_TOKEN` on the git remote if `gh` picks a bot credential that cannot push.

## Lesson 0a: Control D Pipeline Fix (2026-03-15)

## 1. Hardcoded paths break test isolation

**Pattern:** Scripts that hardcode `/etc/controld/...` fail in non-root test environments.
**Rule:** Always use `${CONTROLD_DIR:-/etc/controld}` for any path under the controld config directory. Apply this consistently across all files that reference the directory — not just the main script.

## 2. Generated TOML ≠ Dashboard Attribution

**Pattern:** `ctrld` generates a `ctrld.toml` on start regardless of how it was invoked, but the `--cd <profile_id>` flag is what provides dashboard-level attribution.
**Rule:** Don't confuse the auto-generated local config with proof of dashboard connectivity. The native `--cd` flag is the correct mechanism for profile attribution.

## 3. Test mocks must cover new functions

**Pattern:** Introducing `restart_with_native_profile` broke `test_controld_validation.sh` because only `restart_with_config` was mocked.
**Rule:** When adding a new function to the call path, immediately update all test files that mock functions in that path.

## Lesson 0b: Zero-diff “security” PRs should be closed, not merged (2026-03-21)

**Pattern:** Automation opens a PR whose **body** describes fixes, but `changedFiles == 0` and `gh pr diff` is empty—often because `main` already contains the change.
**Rule:** Close with a short comment linking the finding; do not squash-merge empty commits. Saves queue noise and avoids misleading “merged” history.

## Lesson 0c: Retry merge after “Base branch was modified” (2026-03-21)

**Pattern:** Squash-merging PR A updates `main`; immediate merge of PR B fails with GraphQL _Base branch was modified_.
**Rule:** Re-fetch mergeability and retry B without force-push; no branch rewrite required.

## Lesson 0d: Cursor Cloud pre-commit hook + spaced secret names (2026-03-21)

**Pattern:** `pre-commit.cursor` used `SECRET_VALUE="${!SECRET_NAME}"`. Entries in `CLOUD_AGENT_INJECTED_SECRET_NAMES` can be human-readable labels with spaces (`GitHub SSH Key`), which are **not** valid bash identifier names → `invalid variable name` at commit time.
**Rule:** Resolve values with `printenv "$SECRET_NAME"` (after trimming whitespace from comma-split tokens). Canonical copies: `scripts/cursor_cloud_agent_pre_commit.sh` and `scripts/cursor_cloud_agent_commit_msg.sh`.

## Lesson 0e: Jules “Bolt” PRs may ship 100k-line junk fixtures (2026-03-22)

**Pattern:** A performance-titled PR adds a multi-megabyte `test.txt` of generated hostnames and scratch `test_perf*.py` files.
**Rule:** Treat as **merge blocker** (hygiene + abuse-of-repo signal). Require removal before any squash-merge; do not assume good faith without a minimal reproducible benchmark tied to `docs/TESTING.md` patterns.

## Lesson 0f: Emoji-heavy default branch names can break dependency-submission jobs (2026-03-22)

**Pattern:** `submit-pypi` / GitHub dependency snapshot action failed with `HttpError` on a branch named with leading emoji after syncing `main` into a PR.
**Rule:** When `submit-pypi` fails only on bot branches, check for **ref/encoding** issues before blaming application code; still treat as **merge blocker** unless branch protection marks the job non-required.

## Lesson 0i: IDE background terminal stalling — root cause is 1Password SSH Agent (2026-03-24)

**Pattern:** All `run_command` calls from IDE agents stall indefinitely in repos using 1Password SSH Agent, regardless of Fish prompt theme. Removing Hydro, disabling gitnow, and setting `hydro_fetch false` did NOT fix it. The root cause is 1Password's Touch ID gate: background terminals have no window to display the biometric prompt, so auth blocks forever. This is a confirmed upstream bug (1Password 8.12.x + Apple Keychain, still under investigation).
**Mitigations applied (layered):**

1. **SSH key pinning:** `IdentitiesOnly yes` + `IdentityFile "~/.ssh/GitHub SSH Key.pub"` in `Host github.com` block — reduces agent re-prompting.
2. **Tight timeouts:** `ServerAliveInterval 10`, `ConnectTimeout 10` — connections fail fast instead of hanging forever.
3. **Socket health check:** `config.fish` detects 1Password socket availability and falls back to macOS native agent.
4. **Agent API bypass:** Use GitHub MCP API (`mcp_GitHub_*` tools) for all PR/repo operations instead of `run_command`.

**Verified:** Hydro and gitnow were both eliminated as suspects through systematic removal testing on 2026-03-24.

---

**Pattern:** Attempting to `gh pr review --request-changes` fails with `Can not request changes on your own pull request` when the automation bot is the same identity that opened the PR.
**Rule:** Use `gh pr comment` to leave feedback and manually request resolution instead of using the formal review state for self-authored automated PRs.

## Lesson 0h: IDE background terminal stalling — root cause is 1Password SSH Agent (2026-03-24)

**Pattern:** All `run_command` calls from IDE agents stall indefinitely in repos using 1Password SSH Agent, regardless of Fish prompt theme. Removing Hydro, disabling gitnow, and setting `hydro_fetch false` did NOT fix it. The root cause is 1Password's Touch ID gate: background terminals have no window to display the biometric prompt, so auth blocks forever. This is a confirmed upstream bug (1Password 8.12.x + Apple Keychain, still under investigation).
**Mitigations applied (layered):**

1. **SSH key pinning:** `IdentitiesOnly yes` + `IdentityFile "~/.ssh/GitHub SSH Key.pub"` in `Host github.com` block — reduces agent re-prompting.
2. **Tight timeouts:** `ServerAliveInterval 10`, `ConnectTimeout 10` — connections fail fast instead of hanging forever.
3. **Socket health check:** `config.fish` detects 1Password socket availability and falls back to macOS native agent.
4. **Agent API bypass:** Use GitHub MCP API (`mcp_GitHub_*` tools) for all PR/repo operations instead of `run_command`.

**Verified:** Hydro and gitnow were both eliminated as suspects through systematic removal testing on 2026-03-24.

## Lesson 0k: `actions/labeler@v6` + `pull_request_target` reads **base** `labeler.yml` (2026-03-24)

**Pattern:** A PR updates `.github/labeler.yml` to a new structure, but the `label` workflow still fails with `found unexpected type for label 'documentation'`.
**Root cause:** Workflows using `on: pull_request_target` execute with workflow + config from the **default branch**, not the PR head. Until `main`’s `.github/labeler.yml` matches **labeler v5+ / v6** expectations, PRs will keep failing the label job.
**Rule:** When fixing labeler config for `pull_request_target`, patch **`main` first** (or temporarily switch the workflow to `pull_request` for verification per upstream README). Validate against the **array-of-match-objects** schema from `actions/labeler` README — avoid over-nesting under `any-glob-to-any-file`.

## Lesson 0j: `git push` for PR branch updates must use the same credential as `gh` (2026-04-01)

**Pattern:** `gh pr merge` / API calls authenticate as the user via `GH_TOKEN`, but a plain `git push https://github.com/owner/repo.git` may pick **`cursor[bot]`** (or another secondary host entry) from `~/.config/gh/hosts.yml`, producing **403 Permission denied** even when the user can merge via UI/`gh`.
**Rule:** After `gh auth setup-git`, verify `git push` uses the **intended** identity, or avoid pushes entirely and use **`gh pr merge`** / **`gh workflow run`** / **MCP**. For **Jujitsu (jj)**: treat `jj git push` the same way — ensure remote credentials map to the **human/maintenance PAT**, not a read-only bot. Prefer documenting: “PR branch sync: `gh` API or PAT-in-URL remote,” not unauthenticated HTTPS.

## Lesson 0l: Inventory data can become stale - verify PR existence before triage (2026-04-03)

**Pattern:** PR inventory lists non-existent PRs (e.g., email-security-pipeline #627) causing "Not Found" errors during merge attempts.
**Rule:** Before adding PRs to inventory or attempting merges, verify existence with `get_pull_request`. Inventory should be treated as a snapshot that may drift.

## Lesson 0m: Merge order matters - security before performance (2026-04-03)

**Pattern:** Merging performance PRs first (e.g., Seatek #123) caused security fixes (Seatek #120, #122) to become unmergeable due to conflicts.
**Rule:** When security and performance PRs touch the same files, merge security fixes first. Performance optimizations can be rebased on top of security patches more easily than vice versa.

## Lesson 0n: Duplicate PR patterns indicate automation opportunities (2026-04-03)

**Pattern:** Multiple similar fixes across repos (ANSI stripping, fnmatch optimization, TTY degradation) suggest repetitive automation.
**Rule:** Consider creating shared libraries or common patterns to reduce duplicate PR creation. Track duplicate patterns to identify consolidation opportunities.

## Lesson 0o: GitHub MCP API cannot auto-merge some repos (2026-04-03)

**Pattern:** `mcp4_merge_pull_request` fails with "Pull Request is not mergeable" even when PR has no conflicts and all checks pass. PRs return `merge_commit_sha: null` and `mergeable: null` in API responses.
**Root cause:** Repository settings or branch protection rules may require manual merge approval or lack auto-merge configuration for MCP tools.
**Rule:** When automated merge via MCP tools fails, verify repo settings: (1) Enable auto-merge in repository settings, (2) Check branch protection rules for merge restrictions, (3) Verify MCP token has sufficient permissions. For security PRs that pass all gates, document approval status and provide manual merge instructions via GitHub UI.

## Lesson 0p: Jules zero-diff QA PRs pollute PR list (2026-04-03)

**Pattern:** Automated Jules Daily QA creates PRs with `changedFiles: 0` when QA passes but no code changes are needed. PR body contains valuable findings, but empty diff adds noise to PR list.
**Rule:** Close zero-diff QA PRs immediately with comment acknowledging findings. If QA findings are valuable, extract them to `tasks/lessons.md` or session reports. Configure Jules to skip PR creation when `git diff --stat` shows no changes.
