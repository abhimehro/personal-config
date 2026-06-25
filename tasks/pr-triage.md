# PR Triage — 2026-06-25

## Duplicate & overlap groups

### Group A — personal-config weekly retrospective parallelize
| PR | Files | Keeper | Action |
| --- | --- | --- | --- |
| #1354 | `repository_automation_tasks.py`, `bolt.md` | **#1354** | MERGED |
| #1336 | `repository_automation_tasks.py` only | — | CLOSED → superseded by #1354 |

### Group B — personal-config dashboard metric card ARIA
| PR | Files | Keeper | Action |
| --- | --- | --- | --- |
| #1350 | `analytics_dashboard.sh` | **#1350** | MERGED |
| #1345 | `analytics_dashboard.sh`, `palette.md` | — | CLOSED → duplicate of #1350 |
| #1340 | `analytics_dashboard.sh`, `performance_optimizer.sh` | **#1340** | MERGED after autofix |

### Group C — repoprompt-ce Changelog DateFormatter
| PR | Files | Keeper | Action |
| --- | --- | --- | --- |
| #55 | `Changelog.swift`, `bolt.md` | **#55** | MERGED |
| #52 | + workflow + `PromptPackagingService.swift` | — | CLOSED → superseded by #55 |

### Group D — repoprompt-ce notifications/message a11y
| PR | Files | Keeper | Action |
| --- | --- | --- | --- |
| #53 | `NotificationsButtonView.swift` | **#53** | DEFER (Style) |
| #51 | broader workflow/Package churn | — | CLOSED → superseded by #53 |

## Superseded / zero-diff

| PR | Reason |
| --- | --- |
| Seatek #366 | Zero-diff daily QA PR (0 files changed) |

## Security gate review

| PR | Gate | Result |
| --- | --- | --- |
| Seatek #367 | Fail-fast on missing `git` binary (B607 path hijack) | **PASS → MERGED** |
| personal-config #1352 | SHA-pinned actions → floating `@v*` tags | **FAIL → ESCALATE** |
| repoprompt-ce #41 | Keychain accessibility tighten | **PASS logic; Style fail → DEFER** |

## Deferred tail → Salvage Agent

```yaml
open_followups:
  - repo: abhimehro/personal-config
    pr: 1352
    reason: ESCALATE — SHA→tag action pin regression
  - repo: abhimehro/Hydrograph_Versus_Seatek_Sensors_Project
    pr: 292
    reason: DEFER — submit-pypi infra fail
  - repo: abhimehro/repoprompt-ce
    pr: 41
    reason: DEFER — T1 security salvage; Style fail
  - repo: abhimehro/repoprompt-ce
    pr: 53
    reason: DEFER — Palette a11y; Style fail
  - repo: abhimehro/repoprompt-ce
    pr: 42
    reason: DEFER — dependabot; Style fail
  - repo: abhimehro/repoprompt-ce
    pr: 44
    reason: DEFER — dependabot CONFLICTING + Style/Codacy/snyk
```
