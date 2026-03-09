# PR Triage Findings

Triage basis: 2026-03-09 inventory from `tasks/pr-inventory.md`.

## Author Detection

- Current Jules PRs appear with `author.login=abhimehro`, not a bot login.
- Each in-scope PR in this session matches the delegated-author heuristic:
  - PR body footer contains `PR created automatically by Jules ... started by @abhimehro`
  - PR thread includes the standard bootstrap comment from `google-labs-jules`

## Exact Duplicates / High File Overlap

No exact duplicates detected in the current open queue.

## Overlap / Conflict Groups

| Repo | PRs | Shared Files | Finding | Action |
|---|---|---|---|---|
| abhimehro/[REDACTED]-config | #626, #627 | `.github/workflows/codacy.yml` | File overlap only; not duplicates. Both are independently blocked by security and scope-drift issues. | ESCALATE both; do not merge either. |

## Superseded / Zero-Diff PRs

No zero-diff or clearly superseded PRs detected in the current open queue.

## Security and Quality Findings

| Repo | PR # | Category | Disposition | Findings |
|---|---:|---|---|---|
| abhimehro/[REDACTED]-config | 626 | CI/INFRA | ESCALATE | Security gate fail: changes `codacy/codacy-analysis-cli-action` from an immutable SHA pin to mutable `@v1`. PR body claims auth test additions, but the diff only changes `.github/workflows/codacy.yml`, so the stated intent does not match the actual change set. CI is also failing. |
| abhimehro/[REDACTED]-config | 627 | CI/INFRA | ESCALATE | Security gate fail: changes OSV reusable workflow refs from immutable SHAs to mutable `@v1.8.0` tags and adds `.codacy.yml` exclusions for `tests/**` and `media-streaming/**`, reducing analysis coverage. Code quality gate fail: the new test in `tests/test_infuse_media_server.py` asserts clearly incorrect behavior (for example, `document.txt` as `class=\"file video\"` and double-slash paths), matching external review feedback. |
| abhimehro/ctrld-sync | 628 | REFACTOR | MERGE | Clean single-file test addition in `tests/test_retry_jitter.py`. CI is green, merge state is clean, no security regressions were found, and review feedback is non-blocking. |

## CI Notes

| Repo | PR # | CI Assessment |
|---|---:|---|
| abhimehro/[REDACTED]-config | 626 | Failing checks include `Codacy Security Scan` and `scan-pr / scan-pr`. `scan-pr / scan-pr` fails on deprecated `actions/upload-artifact` usage in the reusable workflow path, but the PR remains blocked independently by the action unpinning regression. |
| abhimehro/[REDACTED]-config | 627 | `Codacy Security Scan` fails in a way that looks partially baseline-related, but the PR also changes scan configuration and unpins workflow refs, so it should not be treated as a safe flaky failure. |
| abhimehro/ctrld-sync | 628 | All observed checks passed (`bandit`, `Codacy Security Scan`, `ruff`, `mypy`, `test`, `CodeQL`). |

## Consolidation

No consolidation candidate identified. The current queue is too small and the blocked PRs are not safe to combine.

## Operational Constraints

| Scope | State |
|---|---|
| Preflight | Passed after fixing `scripts/preflight-gh-pr-automation.sh` config parsing and adding regression coverage in `tests/test_preflight_gh_pr_automation.sh`. |
| Repo capability signal | `ctrld-sync#628` reported `viewerCanUpdate=false`; `[REDACTED]-config` reported `viewerCanEnableAutoMerge=false`. |
| Environment constraint | This automation environment exposes `gh` for read operations only and does not provide a separate GitHub write tool for cross-repo PR mutation, so dispositions were documented but not executed. |

## Ready-to-Execute Human Actions

### Merge Queue

```bash
gh pr merge 628 --repo abhimehro/ctrld-sync --squash --delete-branch
```

### Escalation Notes

Use these findings when requesting human review or leaving a blocking review:

- `[REDACTED]-config#626`: "Security gate fail: this replaces an immutable action SHA with mutable @v1, and the PR body does not match the actual workflow-only diff."
- `[REDACTED]-config#627`: "Security gate fail: this unpins OSV reusable workflows and reduces Codacy scan scope; code quality gate fail: the new test asserts buggy output and should not be merged as written."
