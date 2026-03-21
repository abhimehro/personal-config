# PR triage — backlog cleanup test (2026-03-21)

## Duplicates / superseded

| Repo | PRs | Finding | Action |
|------|-----|---------|--------|
| ctrld-sync | #651 | **Zero diff** (`changedFiles` 0, `gh pr diff` empty). Body describes TOCTOU fixes already consistent with `main`. | **Close #651** with explanation (superseded / nothing to merge) |

No other duplicate groups in this batch (distinct tasks per PR).

## Merge ordering

1. **Security:** `Seatek_Analysis` #95 (path traversal) — merged first.
2. **Remaining non-personal-config:** `Seatek_Analysis` #94, `email-security-pipeline` #558/#559, `Hydrograph_Versus_Seatek_Sensors_Project` #85/#86 — merged; re-checked mergeability between steps where needed.
3. **`personal-config`:** #652 merged first; **#653 retried** after “base branch was modified” from #652.

## Security gates (high level)

- **#95 (Seatek):** Path sandbox via `normalizePath` + `startsWith` with trailing `/`; no new auth/DB/payment paths. **Merged.**
- **#653 (personal-config):** Moves LaunchAgent log paths off world-writable `/private/tmp` to `$HOME/Library/Logs/`. No secrets; **merged** after core tests/CodeQL/dependency-review green. Codacy Security Scan was **in progress / UNSTABLE** — treated like prior runs: optional third-party noise when required checks pass and diff reviewed.
- **#652:** Shell performance-only (`basename`/`dirname` → parameter expansion). No privilege changes. Codacy **cancelled** on rollup — core pipeline green.
- **email / Hydro:** Performance or CLI UX; Bandit/pytest or CodeQL green where applicable.

## CI policy applied

- Did **not** merge with failing **pytest** / **Run All Tests** (personal-config) or primary test jobs on other repos.
- Allowed merge when **Codacy** was cancelled/in progress but **Code Quality**, **CodeQL**, **dependency-review**, and **tests** succeeded and the diff was manually reviewed for security (aligned with `docs/automated-pr-review-agent.md` optional-check guidance).

## Auto-fix

- **None required** this session (no lint-only branches, no trivial conflicts on these PRs).
