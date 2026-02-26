# Lessons Learned — 2026-02-26

- Bot-generated PR streams can include many zero-diff/superseded branches; detect `changed_files_count == 0` early and route to closure queue.
- File-path overlap alone can produce false duplicate positives (same files, different intent); require title/intent confirmation before auto-closing.
- Integration permissions are asymmetric across repos: merge may be allowed in one repo while close/comment/review are blocked elsewhere.
- For multi-repo automated triage, gather immutable evidence first (`inventory`, `triage`) before attempting actions to avoid partial state confusion.
- When close permissions are unavailable, escalate with an explicit list of target PRs and ready-to-use closure rationale comments.
