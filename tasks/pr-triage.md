# PR Triage — 2026-06-24

## Duplicate & overlap groups

### Group A — repoprompt-ce Changelog DateFormatter
| PR | Files | Keeper | Action |
| --- | --- | --- | --- |
| #52 | `Changelog.swift`, `PromptPackagingService.swift` | **#52** | DEFER (Style) |
| #49 | `Changelog.swift`, workflows | — | **CLOSED** → superseded by #52 |

### Group B — repoprompt-ce cross-platform release tests
| PR | Files | Keeper | Action |
| --- | --- | --- | --- |
| #50 | `promote_release.sh`, test scripts, workflows | **#50** | DEFER (Style) |
| #24 (salvage) | `Scripts/promote_release.sh`, test files | — | **CLOSED** → superseded by #50 |

### Group C — repoprompt-ce agent message a11y
| PR | Files | Keeper | Action |
| --- | --- | --- | --- |
| #51 | `AgentMessageBubble.swift`, workflows | **#51** | DEFER (Style) |
| #25 (salvage) | icon button components | — | **CLOSED** → superseded by #51 |

## Infra detection

### personal-config — Codacy Security Scan (repo-wide)
- **Signal:** 10/10 open PRs show `Codacy Security Scan` failure; branches are `MERGEABLE` (not conflicted).
- **Classification:** Suspected `main`-side infra breakage (Lesson 0t pattern).
- **Action:** DEFER entire queue; no salvage drafts opened. Escalate for human Codacy triage.

### repoprompt-ce — Style check cluster
- **Signal:** 9/9 open PRs fail `Style` (+ ancillary Codacy/snyk/build).
- **Note:** T0 infra-fix #29 merged 2026-06-23; `update-branch` returns benign 422 (branches current).
- **Action:** DEFER; dedupe complete. T1 #41 awaits Style fix on `main` or formatter run.

### Hydrograph — submit-pypi
- **Signal:** dependabot #292 fails `submit-pypi` only.
- **Action:** DEFER; not a merge conflict.

## Security gate review

| PR | Gate | Result |
| --- | --- | --- |
| repoprompt-ce #41 | Keychain accessibility tighten | **PASS logic** — draft salvage; Style blocked |
| personal-config dependabot cluster | Gate 4 CI/INFRA | **PASS** — version bumps only; blocked by Codacy infra |

## Phase 2 actions taken

| Repo | Old PR | Disposition | Notes |
| --- | ---: | --- | --- |
| repoprompt-ce | #49 | CLOSE-DUPLICATE | Superseded by #52 |
| repoprompt-ce | #24 | CLOSE-DUPLICATE | Superseded by #50 |
| repoprompt-ce | #25 | CLOSE-DUPLICATE | Superseded by #51 |

## Deferred tail → next session

```yaml
open_followups:
  - repo: abhimehro/personal-config
    pr: all-open
    reason: T0 — Codacy Security Scan failing on every open PR
  - repo: abhimehro/repoprompt-ce
    pr: 41
    reason: T1 — Keychain salvage v3; Style blocked
  - repo: abhimehro/repoprompt-ce
    pr: 50
    reason: T3 — cross-platform test salvage; Style blocked
  - repo: abhimehro/repoprompt-ce
    pr: 51
    reason: T3 — Palette a11y; Style blocked
  - repo: abhimehro/repoprompt-ce
    pr: 52
    reason: T3 — Bolt DateFormatter; Style blocked
  - repo: abhimehro/Hydrograph_Versus_Seatek_Sensors_Project
    pr: 292
    reason: submit-pypi check failing
```

## Ready-to-Execute Human Actions

### Phase 1 merge burst (CLEAN dependabot — not executed by salvage per S1)

```bash
# ctrld-sync (5 PRs, all CLEAN)
gh pr merge 938 --repo abhimehro/ctrld-sync --squash --delete-branch
gh pr merge 939 --repo abhimehro/ctrld-sync --squash --delete-branch
gh pr merge 940 --repo abhimehro/ctrld-sync --squash --delete-branch
gh pr merge 941 --repo abhimehro/ctrld-sync --squash --delete-branch
gh pr merge 942 --repo abhimehro/ctrld-sync --squash --delete-branch

# email-security-pipeline
gh pr merge 1146 --repo abhimehro/email-security-pipeline --squash --delete-branch
gh pr merge 1147 --repo abhimehro/email-security-pipeline --squash --delete-branch

# Seatek_Analysis + series_correction
gh pr merge 360 --repo abhimehro/Seatek_Analysis --squash --delete-branch
gh pr merge 149 --repo abhimehro/series_correction_project_updated --squash --delete-branch
```

### Infra triage (before merging personal-config / repoprompt-ce bot PRs)

1. Investigate **Codacy Security Scan** on `abhimehro/personal-config` `main`.
2. Run `make dev-format-check` / `make dev-lint` on repoprompt-ce `main`; open T0 infra-fix if Style is red on `main`.
