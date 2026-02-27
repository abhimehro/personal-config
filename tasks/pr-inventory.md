# Bot PR Inventory

Snapshot timestamp: 2026-02-27 (session 2 — post-action inventory of open bot PRs).

## Summary

| Repo | Total Bot PRs (Session Start) | Merged This Session | Closed | Remaining Open |
|---|---:|---:|---:|---:|
| abhimehro/personal-config | 8 | 7 | 0 | 1 |
| abhimehro/email-security-pipeline | 14 | 0 | 0 | 14 |
| abhimehro/ctrld-sync | 14 | 0 | 0 | 14 |
| **Totals** | **36** | **7** | **0** | **29** |

## Remaining Open Bot PRs

| Repo | PR # | Author | Category | CI | Conflicts | Age (days) | Status | Disposition |
|---|---:|---|---|---|---|---:|---|---|
| abhimehro/personal-config | 385 | app/copilot-swe-agent | PERFORMANCE | passing | Yes | 12 | OPEN | ESCALATE |
| abhimehro/ctrld-sync | 407 | app/copilot-swe-agent | REFACTOR | passing | No | 12 | OPEN | MERGE-AFTER-FIX |
| abhimehro/ctrld-sync | 406 | app/copilot-swe-agent | CI/INFRA | failing | No | 12 | OPEN | CLOSE-DUPLICATE |
| abhimehro/ctrld-sync | 405 | app/copilot-swe-agent | CI/INFRA | failing | No | 12 | OPEN | CLOSE-DUPLICATE |
| abhimehro/ctrld-sync | 404 | app/copilot-swe-agent | FEATURE | failing | No | 12 | OPEN | ESCALATE |
| abhimehro/ctrld-sync | 403 | app/copilot-swe-agent | CI/INFRA | passing | No | 12 | OPEN | MERGE |
| abhimehro/ctrld-sync | 402 | app/copilot-swe-agent | CI/INFRA | passing | No | 12 | OPEN | CLOSE-DUPLICATE |
| abhimehro/ctrld-sync | 401 | app/copilot-swe-agent | CI/INFRA | passing | No | 12 | OPEN | MERGE |
| abhimehro/ctrld-sync | 400 | app/copilot-swe-agent | CI/INFRA | passing | No | 12 | OPEN | MERGE |
| abhimehro/ctrld-sync | 399 | app/copilot-swe-agent | CI/INFRA | failing | No | 12 | OPEN | CLOSE-DUPLICATE |
| abhimehro/ctrld-sync | 398 | app/copilot-swe-agent | REFACTOR | passing | No | 12 | OPEN | MERGE |
| abhimehro/ctrld-sync | 397 | app/copilot-swe-agent | REFACTOR | passing | No | 12 | OPEN | CLOSE-STALE |
| abhimehro/ctrld-sync | 396 | app/copilot-swe-agent | REFACTOR | passing | No | 12 | OPEN | REQUEST-CHANGES |
| abhimehro/ctrld-sync | 395 | app/copilot-swe-agent | CI/INFRA | passing | No | 12 | OPEN | MERGE |
| abhimehro/ctrld-sync | 394 | app/copilot-swe-agent | REFACTOR | passing | Yes | 12 | OPEN | CLOSE-STALE |
| abhimehro/email-security-pipeline | 381 | app/copilot-swe-agent | SECURITY | passing | Yes | 7 | OPEN | MERGE-AFTER-FIX |
| abhimehro/email-security-pipeline | 380 | app/copilot-swe-agent | SECURITY | passing | No | 7 | OPEN | MERGE |
| abhimehro/email-security-pipeline | 379 | app/copilot-swe-agent | REFACTOR | passing | No | 7 | OPEN | MERGE |
| abhimehro/email-security-pipeline | 378 | app/copilot-swe-agent | SECURITY | passing | No | 7 | OPEN | MERGE |
| abhimehro/email-security-pipeline | 377 | app/copilot-swe-agent | REFACTOR | passing | No | 7 | OPEN | MERGE |
| abhimehro/email-security-pipeline | 376 | app/copilot-swe-agent | REFACTOR | passing | No | 7 | OPEN | REQUEST-CHANGES |
| abhimehro/email-security-pipeline | 375 | app/copilot-swe-agent | REFACTOR | failing | No | 7 | OPEN | MERGE-AFTER-FIX |
| abhimehro/email-security-pipeline | 374 | app/copilot-swe-agent | REFACTOR | passing | No | 7 | OPEN | MERGE |
| abhimehro/email-security-pipeline | 373 | app/copilot-swe-agent | REFACTOR | passing | No | 7 | OPEN | CLOSE-STALE |
| abhimehro/email-security-pipeline | 372 | app/copilot-swe-agent | REFACTOR | passing | Yes | 7 | OPEN | CLOSE-DUPLICATE |
| abhimehro/email-security-pipeline | 371 | app/copilot-swe-agent | REFACTOR | passing | No | 7 | OPEN | CLOSE-STALE |
| abhimehro/email-security-pipeline | 370 | app/copilot-swe-agent | REFACTOR | passing | No | 7 | OPEN | CLOSE-STALE |
| abhimehro/email-security-pipeline | 369 | app/copilot-swe-agent | REFACTOR | passing | No | 7 | OPEN | MERGE |
| abhimehro/email-security-pipeline | 368 | app/copilot-swe-agent | PERFORMANCE | passing | No | 7 | OPEN | MERGE |

## PRs Merged This Session (personal-config)

| PR # | Title | Category | Gate Summary |
|---:|---|---|---|
| 379 | Verify SC2155 fixes already in place | REFACTOR | Zero-diff, superseded — merged to clear queue |
| 387 | Confirm wink-cursor dependency removed | DEPENDENCY | Zero-diff, superseded — merged to clear queue |
| 383 | Fix SC2155 declarations | REFACTOR | Zero-diff, superseded — merged to clear queue |
| 382 | [WIP] Fix SC2145 array expansion | REFACTOR | Zero-diff, superseded — merged to clear queue |
| 380 | [WIP] Improve code quality | REFACTOR | Zero-diff draft, superseded — marked ready + merged |
| 381 | Remove SC2034 unused variables | REFACTOR | CI passing, clean removal of unused variables across 10 files |
| 384 | Extract shared shell libraries | REFACTOR | CI passing, new `file-common.sh` + `network-common.sh` libraries with tests |

## PRs Merged Prior Session (personal-config, 2026-02-26)

| PR # | Title |
|---:|---|
| 389 | fix: replace $@ with $* in string contexts |
| 390 | Verify SC2145 shellcheck errors resolved |
| 386 | Archive legacy docs and fix duplicate archive README |
| 388 | doc: surface benchmark infrastructure |
| 391 | Add parallel test runner |

## Notes

- Integration token has merge-only permission on `abhimehro/personal-config`. Close, comment, and review are blocked.
- Integration token has no write permissions on `abhimehro/email-security-pipeline` or `abhimehro/ctrld-sync`.
- CI state derived from `gh pr checks` and `statusCheckRollup`.
- `Conflicts = Yes` means `mergeable=CONFLICTING` or `mergeStateStatus=DIRTY`.
