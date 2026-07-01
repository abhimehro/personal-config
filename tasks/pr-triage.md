# PR Triage — 2026-07-01

## Duplicate & overlap groups

### Group A — ctrld Palette ANSI isatty guards
| PR | Status | Action |
|----|--------|--------|
| #963 | CLOSED | Duplicate of #965; older approach |
| #965 | OPEN | DEFER — CI failing; salvage after main settles |

### Group B — personal-config parse_inventory tests
| PR | Status | Action |
|----|--------|--------|
| #1440 | CLOSED | Superseded by merged #1433 |
| #1433 | MERGED | Canonical salvage |

### Group C — email-security-pipeline zero-diff Sentinel
| PR | Status | Action |
|----|--------|--------|
| #1199 | CLOSED | Zero-diff; no file changes vs main |

### Group D — Seatek daily QA no-op
| PR | Status | Action |
|----|--------|--------|
| #389 | CLOSED | Zero-diff QA review |

### Group E — dependabot ruby/setup-ruby cluster (5 repos)
All independent workflow bumps; merged in batch: ctrld #966, esp #1198, Seatek #387, hg #308, sc #165.

## Escalations

| Repo | PR | Reason |
|------|---:|--------|
| personal-config | 1443 | SHA→tag workflow pin regression (`actions/github-script@…` → `@v9.0.0`) |
| email-security-pipeline | 1190 | 28-file Daily QA bundle; gh-aw **downgrade** v0.81.6→v0.80.9; merge conflicts |

## Deferred tail (salvage agent)

| Repo | PR | Blocker |
|------|---:|---------|
| personal-config | 1434 | `Run All Tests` failing |
| personal-config | 1438, 1442, 1446 | Merge conflicts after session merges |
| ctrld-sync | 965 | CI failing (Palette) |
| email-security-pipeline | 1178, 1179, 1200 | Merge conflicts |
| email-security-pipeline | 1195 | CI failing (workflow permissions) |
| series_correction_project_updated | 166 | CI failing |

## Merge ordering applied

1. Dependabot DEPENDENCY (5 repos)
2. SECURITY fix ctrld #967
3. email-security-pipeline salvage + formatting (#1192–#1196, #1201, #1180)
4. personal-config salvage cluster (#1433–#1437, #1439, #1422–#1423, #1445)
5. Hydrograph + repoprompt-ce performance/UI

Re-validated mergeability after each batch per Lesson 0.
