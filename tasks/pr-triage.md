# PR Triage — 2026-07-04

## Duplicate / superseded

| PR | Disposition | Reason |
|----|-------------|--------|
| personal-config #1476 | **CLOSE** | Zero-diff Jules QA report (0 files changed) |
| ctrld-sync #977 | **CLOSE** | `main.py` cancel newline fix already landed via merged salvage #974; only journal entry remains |

## Merge queue (ordered)

| Order | PR | Disposition | Rationale |
|------:|----|-------------|-------------|
| 1 | ctrld-sync #978 | **MERGE** | Test-only Bandit hygiene (B108 path, B104 nosec); all gates pass |
| 2 | Seatek_Analysis #400 | **MERGE** | Routine dependabot `ruby/setup-ruby` patch bump |
| 3 | Hydrograph #316 | **MERGE** | Routine dependabot `ruby/setup-ruby` patch bump |
| 4 | Seatek_Analysis #402 | **MERGE** | Single R comment line-length lint autofix |
| 5 | email-security-pipeline #1213 | **MERGE** | Cosmetic CLI icon consistency (`❌` → `✘`); no logic change |
| 6 | Hydrograph #318 | **MERGE** | Removes committed debris/temp scripts; flake8 spacing fix; EOF newline in `github-app.yml` |
| 7 | personal-config #1478 | **MERGE** | `performance_optimizer.sh` single-pass `vm_stat` awk (distinct from merged #1471 `system_metrics.sh`) |
| 8 | personal-config #1479 | **MERGE** | Extends merged #1471 with combined uptime awk pass in `system_metrics.sh` |
| 9 | repoprompt-ce #88 | **MERGE** | Accessibility label on icon-only button |
| 10 | repoprompt-ce #89 | **MERGE** | `String.fileExtension` allocation optimization; no auth/secrets |

## Escalations

None — all open PRs have green required CI, no security gate failures, no trust-boundary workflow rewrites.

## Stale (>30 days)

None.

## Conflict watch

- personal-config #1479 touches `system_metrics.sh` after #1471 merge — re-check mergeability before squash.
- ctrld #977 superseded by #974 — do not merge.
