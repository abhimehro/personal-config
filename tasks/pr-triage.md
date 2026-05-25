# PR Triage — 2026-05-25

## Phase 1 dispositions

| Disposition | Count | PRs |
| --- | ---: | --- |
| MERGE | 10 | personal-config #1050, #1053–#1055, #1060, #1063; email-security #925, #926; Seatek #222 |
| MERGE-AFTER-FIX | 1 | personal-config #1050 (CWE-94 preamble restored) |
| CLOSE-DUPLICATE / SUPERSEDED | 2 | personal-config #1057, #1062 |
| DEFER | 12 | personal-config #1051, #1052; email-security #905–908, #913, #917, #921, #927; Seatek #209–214; series_correction #66, #68 |
| ESCALATE | 2 | email-security #919; ctrld-sync #846 (failing required benchmark) |

## Duplicate / overlap groups

### `scratch_triage.py` cluster

| Keeper | Closed / reason |
| --- | --- |
| **#1063** (autofix `main` guard) | #1057 closed — overlapping perf edit + CodeScene fail |
| — | #1062 closed — conflicts after #1063; parallel `gh pr list` superseded |
| #1051 | **DEFER** — larger modularize salvage; CodeScene fail; reconcile after #1063 on main |

### Salvage PRs (Phase 2 carryover)

| PR | Action |
| --- | --- |
| #1050 | **MERGED** — salvages #1036 tracker; auto-fix restored CWE-94 YAML preamble |
| #1052 | **DEFER** — salvages #1039 PAT runbook; no `parse_inventory.py`; CodeScene red |
| #1051 | **DEFER** — salvages #1048; overlaps merged #1063 |

## Merge order executed

1. personal-config #1053 (docs), #1054, #1055, #1060 (low-risk / docs / perf)
2. personal-config #1063 (scratch_triage autofix)
3. Close #1062, #1057
4. Auto-fix + merge #1050
5. email-security #925, #926
6. Seatek #222

## Ready-to-execute human actions

```bash
# Rebase conflicting email-security Bolt queue (oldest first)
for pr in 905 906 907 908 913 917 921 927; do
  gh api -X PUT "repos/abhimehro/email-security-pipeline/pulls/${pr}/update-branch" || true
  gh pr merge "$pr" -R abhimehro/email-security-pipeline --squash --delete-branch
done

# Human review before merge (security-classified repo)
gh pr view 919 -R abhimehro/email-security-pipeline

# CodeScene-blocked salvage PRs
gh pr checks 1051 -R abhimehro/personal-config
gh pr checks 1052 -R abhimehro/personal-config

# ctrld-sync benchmark regression
gh pr checks 846 -R abhimehro/ctrld-sync
```

## Security gate notes

- Gate 2 **pass** on all merged PRs (GitGuardian/CodeQL green where required).
- **#1050:** Restored CWE-94 preamble comments removed by action SHA pin hunks; tests green before merge.
- **#919:** TOCTOU config permission fix — **ESCALATE** (do not auto-merge in `email-security-pipeline` without human sign-off).
- **Never merged:** PRs with failing required checks (CodeScene, benchmark) or unresolved conflicts.
