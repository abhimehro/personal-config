# PR triage — backlog cleanup test (2026-03-22)

## Duplicates / superseded

| Repo | PRs | Finding | Action |
|------|-----|---------|--------|
| — | — | No exact duplicate groups identified among open automation PRs | — |

## Merge ordering (executed)

1. `email-security-pipeline` **#566** — independent repo; squash-merged first.
2. `personal-config` **#660** — security-hardening shell changes; squash-merged after review of `eval` removals.
3. `ctrld-sync` **#655** — auto-fix **Ruff F401** (`conftest.py` unused `pytest` import), then squash-merged after CI green.

**Post-merge:** Re-listed open PRs; no additional merges performed on remaining items (gates failed or escalated).

## Security gates (summary)

| PR | Gate 1 CI | Gate 2 security | Decision |
|----|-----------|-------------------|----------|
| 566 | Green | No secrets/`eval`/shell injection in diff sample | **MERGE** |
| 660 | Core green; `label` fail treated as optional noise | `printf -v` / indirect expansion replaces `eval`; large formatting churn — reviewed hotspots | **MERGE** |
| 655 | Green after fix | `api_client.py` threading snapshot — no auth/payment/DB | **MERGE** |
| 658 | Core green | **Hygiene fail:** 100k-line generated `test.txt` | **REQUEST-CHANGES** (comment) |
| 659 | Incomplete + conflicts | **Scope creep** (Docker, `.cursor`, network libs) | **ESCALATE** (comment) |
| 565 | Green / draft | **Supply-chain:** SHA pins → mutable tags | **ESCALATE** (comment) |
| 656 | CodeScene + submit-pypi fail | UX-only intent; failures not proven unrelated | **REQUEST-CHANGES** (comment); no merge |

## Auto-fix

| Repo | PR | Fix |
|------|-----|-----|
| ctrld-sync | 655 | Removed unused `import pytest` from `conftest.py`; pushed to head branch. |
| ctrld-sync | 656 | Merged latest `main` into PR branch so `conftest` lint fix applies (ruff then green); **other checks still failing**. |

## CI policy notes

- Did **not** merge with failing **ruff**, **CodeScene**, or ambiguous **submit-pypi** on #656.
- Did **not** merge **#565** due to supply-chain policy (mutable action tags), regardless of green auxiliary checks.
- `label` failures on personal-config PRs treated as non-blocking when **Run All Tests**, **CodeQL**, **dependency-review**, and **Shell/Python quality** were green and diff reviewed (consistent with prior session playbook).
