# Lessons Learned

## Lesson 0: Multi-repo automated PR merges need sequential re-validation
**Pattern:** After squash-merging one automation PR, sibling PRs from the same bot often become **CONFLICTING** with `main`.
**Rule:** Re-run mergeability after each merge; merge `origin/main` into the PR branch and resolve conflicts with ordinary commits (never force-push). Use `GH_TOKEN` on the git remote if `gh` picks a bot credential that cannot push.

## Lesson 0f: Self-review failures with GitHub API (2026-03-22)
**Pattern:** Attempting to `gh pr review --request-changes` fails with `Can not request changes on your own pull request` when the automation bot is the same identity that opened the PR.
**Rule:** Use `gh pr comment` to leave feedback and manually request resolution instead of using the formal review state for self-authored automated PRs.

## Lesson 0a: Zero-diff “security” PRs should be closed, not merged (2026-03-21)
**Pattern:** Automation opens a PR whose **body** describes fixes, but `changedFiles == 0` and `gh pr diff` is empty—often because `main` already contains the change.
**Rule:** Close with a short comment linking the finding; do not squash-merge empty commits. Saves queue noise and avoids misleading “merged” history.

## Lesson 0b: Retry merge after “Base branch was modified” (2026-03-21)
**Pattern:** Squash-merging PR A updates `main`; immediate merge of PR B fails with GraphQL *Base branch was modified*.
**Rule:** Re-fetch mergeability and retry B without force-push; no branch rewrite required.

## Lesson 0c: Cursor Cloud pre-commit hook + spaced secret names (2026-03-21)
**Pattern:** `pre-commit.cursor` used `SECRET_VALUE="${!SECRET_NAME}"`. Entries in `CLOUD_AGENT_INJECTED_SECRET_NAMES` can be human-readable labels with spaces (`GitHub SSH Key`), which are **not** valid bash identifier names → `invalid variable name` at commit time.
**Rule:** Resolve values with `printenv "$SECRET_NAME"` (after trimming whitespace from comma-split tokens). Canonical copies: `scripts/cursor_cloud_agent_pre_commit.sh` and `scripts/cursor_cloud_agent_commit_msg.sh`.

## Lesson 0d: Jules “Bolt” PRs may ship 100k-line junk fixtures (2026-03-22)
**Pattern:** A performance-titled PR adds a multi-megabyte `test.txt` of generated hostnames and scratch `test_perf*.py` files.
**Rule:** Treat as **merge blocker** (hygiene + abuse-of-repo signal). Require removal before any squash-merge; do not assume good faith without a minimal reproducible benchmark tied to `docs/TESTING.md` patterns.

## Lesson 0e: Emoji-heavy default branch names can break dependency-submission jobs (2026-03-22)
**Pattern:** `submit-pypi` / GitHub dependency snapshot action failed with `HttpError` on a branch named with leading emoji after syncing `main` into a PR.
**Rule:** When `submit-pypi` fails only on bot branches, check for **ref/encoding** issues before blaming application code; still treat as **merge blocker** unless branch protection marks the job non-required.

---

## Lessons Learned — Control D Pipeline Fix (2026-03-15)

## Lesson 1: Hardcoded paths break test isolation
**Pattern:** Scripts that hardcode `/etc/controld/...` fail in non-root test environments.
**Rule:** Always use `${CONTROLD_DIR:-/etc/controld}` for any path under the controld config directory. Apply this consistently across all files that reference the directory — not just the main script.

## Lesson 2: Generated TOML ≠ Dashboard Attribution
**Pattern:** `ctrld` generates a `ctrld.toml` on start regardless of how it was invoked, but the `--cd <profile_id>` flag is what provides dashboard-level attribution.
**Rule:** Don't confuse the auto-generated local config with proof of dashboard connectivity. The native `--cd` flag is the correct mechanism for profile attribution.

## Lesson 3: Test mocks must cover new functions
**Pattern:** Introducing `restart_with_native_profile` broke `test_controld_validation.sh` because only `restart_with_config` was mocked.
**Rule:** When adding a new function to the call path, immediately update all test files that mock functions in that path.
