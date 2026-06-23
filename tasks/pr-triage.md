# PR Triage — 2026-06-23 (Phase 2 Salvage)

## Duplicate & overlap groups resolved

### Group A — personal-config dashboard a11y
| PR | Files | Keeper | Action |
| --- | --- | --- | --- |
| #1326 | `analytics_dashboard.sh`, `performance_optimizer.sh`, `.codacy.yml` | **#1326** | KEEP |
| #1329 | `analytics_dashboard.sh`, `.jules/palette.md` | — | **CLOSED** → duplicate of #1326 |

### Group B — ctrld-sync mypy/ruff fix
| PR | Files | Keeper | Action |
| --- | --- | --- | --- |
| #943 | `main.py`, `pr_payload.json` | **#943** | KEEP (CLEAN green, T0) |
| #936 (draft) | `main.py` | — | **CLOSED** → superseded by #943 |

### Group C — repoprompt-ce Changelog DateFormatter
| PR | Files | Keeper | Action |
| --- | --- | --- | --- |
| #49 | `Changelog.swift` (+ minimal deps) | **#49** | KEEP; cherry-pick Changelog only if merging |
| #39 | `Changelog.swift` + workflow/LICENSE/README churn | — | **CLOSED** → superseded by #49 |

### Group D — repoprompt-ce icon button a11y
| PR | Files | Keeper | Action |
| --- | --- | --- | --- |
| #25 (salvage) | 5 button components | **#25** | DEFER (main CI) |
| #48 (Palette) | `NotificationsButtonView.swift` only | — | **CLOSED** → duplicate of #25 |

### Group E — repoprompt-ce Linux release tests
| PR | Files | Keeper | Action |
| --- | --- | --- | --- |
| #24 (salvage) | `promote_release.sh`, test tooling | **#24** | DEFER (main CI) |
| #47 (Jules) | workflows + Package.swift + tests | — | **CLOSED** → duplicate of #24 |

### Group F — series_correction perf tail
| PR | Status | Keeper | Action |
| --- | --- | --- | --- |
| #135, #142 | CLOSED (CodeScene) | **#144** | Prior tail resolved; #144 CLEAN green |

## Incompatible dependency closes

| PR | Reason |
| --- | --- |
| Seatek #351 | `numpy>=2.5.0` requires Python >=3.12; validate workflow runs Python 3.11 |

## Infra detection

| Repo | Signal | Classification |
| --- | --- | --- |
| ctrld-sync | `main` ruff/mypy fail; 5 dependabot PRs share failure | **Blocked by main** — merge #943 first |
| repoprompt-ce | `main` Style/snyk/build fail; salvage #24/#25/#41 blocked | **Blocked by main** — no new infra-fix drafted (#29 already merged) |
| personal-config | Codacy Security Scan fail across open PRs | **Transient/policy** — not repo-wide main breakage |
| Seatek_Analysis | validate Python version mismatch | **PR-specific** — closed incompatible bump |

## Security gate review

| PR | Gate | Result |
| --- | --- | --- |
| repoprompt-ce #41 | Keychain accessibility tighten (salvage v3) | **T1 draft** — human merge required |
| repoprompt-ce #49 | Changelog perf only | **PASS scope** — avoid workflow file churn on merge |
| email-security-pipeline #1144 | Palette error styling | **PASS** — CLEAN green |

## Deferred tail → next session

```yaml
open_followups:
  - repo: abhimehro/ctrld-sync
    pr: 943
    reason: T0 human merge — unblocks main + dependabot cluster
  - repo: abhimehro/repoprompt-ce
    pr: 41
    reason: T1 human merge — Keychain salvage v3
  - repo: abhimehro/repoprompt-ce
    pr: 24
    reason: DEFER — main Style/snyk/build cluster
  - repo: abhimehro/repoprompt-ce
    pr: 25
    reason: DEFER — main Style/snyk/build cluster
  - repo: abhimehro/repoprompt-ce
    pr: 49
    reason: DEFER — DateFormatter keeper; cherry-pick Changelog only
```
