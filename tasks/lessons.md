# Lessons Learned

## Session 1 — 2026-02-26

- Bot-generated PR streams can include many zero-diff/superseded branches; detect `changed_files_count == 0` early and route to closure queue.
- File-path overlap alone can produce false duplicate positives (same files, different intent); require title/intent confirmation before auto-closing.
- Integration permissions are asymmetric across repos: merge may be allowed in one repo while close/comment/review are blocked elsewhere.
- For multi-repo automated triage, gather immutable evidence first (`inventory`, `triage`) before attempting actions to avoid partial state confusion.
- When close permissions are unavailable, escalate with an explicit list of target PRs and ready-to-use closure rationale comments.

## Session 2 — 2026-02-27

- **Merge-only tokens unblock queue clearance**: Even without close/comment permissions, zero-diff PRs can be squash-merged to clear the queue (the merge is effectively a no-op on the codebase).
- **Draft PRs can be merged after `gh pr ready`**: The `gh pr ready` command works with merge-only permissions, enabling draft zero-diff PRs to be cleared.
- **Post-merge conflict cascade**: Merging a substantial refactor (#384: shared shell libraries) caused #385 to develop conflicts. When merging multiple PRs in sequence, re-check mergeable state after each merge.
- **CI failure patterns in bot PRs**: The copilot-swe-agent's parallel pytest PRs (#406, #399) consistently fail CI because they add `pytest-xdist` as a dependency without updating the lockfile or pyproject.toml correctly. This is a recurring agent misconfiguration.
- **Validator return-value risk**: Dead-code removal PRs that strip `return True` from validation functions can silently break callers that check the return value. Always verify downstream usage before approving dead-code PRs.
- **Security review wins**: `email-security-pipeline#378` (endswith fix) and `#369` (ReDoS-safe regex compilation) are high-value security improvements hiding in REFACTOR-categorized PRs. Category classification should account for security implications, not just primary intent.
- **Lockfile scope creep**: Docstring-only PRs (#407) that modify `uv.lock` to add `pytest-benchmark` are a sign the bot ran extra commands during development. Review lockfile changes in every PR, even documentation PRs.
- **Permission remediation is the largest ROI item**: 22 reviewed-and-ready PRs are blocked solely by missing write permissions on 2 repos. Fixing the integration's permission scope would immediately unlock ~200 minutes of human review savings.

## Session 3 — 2026-02-28

- **Jules is creating massive duplication**: 5 PRs for the same privilege-escalation fix, 6+ PRs for the same interactive menu improvement, 2 PRs for the same TOCTOU fix. The bot does not check for existing open PRs before creating new ones. Configure Jules to check for open PRs with overlapping file paths before creating new ones.
- **Merge cascade creates conflict waves**: Merging 13 PRs in sequence caused ~14 remaining PRs to develop merge conflicts because Jules created many PRs that all touch the same files (`network-mode-manager.sh`, `controld-manager`, AdGuard scripts). Merge ordering matters less than reducing the total number of overlapping PRs at source.
- **Security PRs should merge first**: The 5 security PRs merged cleanly because they were independent of each other. The conflict cascade only started affecting UI/menu PRs after the security PRs changed the shared files.
- **Zero-diff PRs persist**: #417 had zero files changed. This is the same pattern from sessions 1-2 where Jules creates verification-only PRs.
- **Auth-adjacent changes require caution**: #413 modifies profile ID handling in `controld-manager` with env var support and `sudo env` propagation. Even though it's a security improvement, it touches auth-adjacent logic and should be reviewed manually.
- **Batch close commands accelerate cleanup**: Since we can merge but not close, providing the user with ready-to-run `gh pr close` commands for the entire duplicate queue saves significant time.

## Session 4 — 2026-03-08

- **Jules can masquerade as the triggering human author**: Current PRs showed `author.login=abhimehro`, but the PR body/footer and the bootstrap comment from `google-labs-jules` confirmed they were bot-generated. Author-login filtering alone will miss active Jules queues.
- **Delegated-author heuristic is reliable enough for triage**: Treat a PR as Jules-authored when both signals are present: the footer says `PR created automatically by Jules ... started by @<user>` and a `google-labs-jules` comment appears on the thread.
- **Scope creep is now the dominant Jules failure mode**: Recent PRs frequently include generated `.trunk/plugins/trunk` churn, `.jules/*.md`, `tasks/lessons.md`, or unrelated single-line test edits. These should usually be stripped before merge rather than blocking otherwise good changes.
- **Tiny unrelated hunks create avoidable conflict waves**: `ctrld-sync#622` and `#623` both carried the same stray `tests/test_ux.py` change, which would create unnecessary overlap despite different primary intents.
- **The preflight gate itself needs regression coverage**: The session initially failed because `scripts/preflight-gh-pr-automation.sh` used a `sed` range that ended on the same `repos:` line it started on. Config parsing is security-critical for safe automation and should stay covered by tests.

## Session 5 — 2026-03-09

- **Jules test-improvement tasks can smuggle CI security regressions**: `[REDACTED]-config#626` and `#627` were presented as test additions, but the actual diffs changed workflow action references from pinned SHAs to mutable tags and altered scan configuration. For Jules-authored "test" PRs, always inspect workflow and config files before trusting the summary.
- **Reduced scanner scope is a security blocker even in test PRs**: Adding `.codacy.yml` exclusions for `tests/**` and large source directories is not harmless cleanup; it weakens review depth and should fail the security gate unless explicitly approved.
- **Preflight recovery should be validated immediately on the real config**: Fixing the config parser was not enough by itself; rerunning the actual session preflight right after the regression test caught environment-specific issues early and prevented a false sense of readiness.

## 2024-05-24 - Parallel Test Sandboxing & PATH Modification
**Learning:** Shell scripts that modify `PATH` by explicitly appending it rather than prepending to it (e.g., `export PATH="/usr/bin:$PATH"`) can break out of test sandboxes if they are invoked from parallel test runners (like `run_all_tests.sh`) that rely on mocked executables placed at the beginning of the `PATH` (e.g., `export PATH="$MOCK_BIN:$PATH"`). Because `/usr/bin` forces the system path first, it bypasses the mock directory. This can cause mock commands (like `pkill`) to run the real system binary, terminating unrelated tests executing in parallel.
**Action:** When a script requires adding specific paths to `PATH`, always append them (`export PATH="$PATH:/new/path"`) unless there is a critical reason to override the user's environment. This guarantees that mock environments remain properly isolated during test suite execution.
