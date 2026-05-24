# PR Triage — 2026-05-24

## Phase 1 dispositions

| Disposition | Count | PRs |
| --- | ---: | --- |
| MERGE | 8 | personal-config #1037, #1038, #1040, #1041, #1045, #1046; email-security-pipeline #901 |
| CLOSE-DUPLICATE | 3 | personal-config #1042, #1043, #1044 |
| ESCALATE | 2 | personal-config #1039, #1047 (`parse_inventory.py` trust boundary) |
| DEFER | 2 | personal-config #1036 (overlap + conflict after merge wave), #1048 (CodeScene fail) |

## Duplicate / overlap groups

### CWE-94 workflow + regression tests

| Keeper | Closed / reason |
| --- | --- |
| **#1037** (workflow env binding) | — merged first |
| **#1045** (`test_copilot_setup_steps_workflow.py`) | #1044 duplicate + failing CodeScene |
| **#1038** (`test_copilot_setup_steps_cwe94.py` + malicious payload) | merged after test fix for preamble comment |
| #1042 | closed — workflow fix in #1037; CodeScene red |
| #1043 | closed — todo-only verification; superseded |

### PR automation toolchain (`parse_inventory.py`, merge helpers)

| PR | Action |
| --- | --- |
| #1039, #1047 | **ESCALATE** — human review required (agent spec + session memory) |

### Tracker / Jules

| PR | Action |
| --- | --- |
| #1036 | **DEFER** — rebase after #1037; drop duplicate workflow hunks |
| #1048 | **DEFER** — CodeScene required check failing on `scratch_triage.py` |

## Merge order executed

1. #1037 (CWE-94 fix)
2. #1045 (regression tests)
3. Close #1042, #1043, #1044
4. Rebase/fix conflicts → #1040, #1041, #1038, #1046
5. #1046, #1038 (after auto-fix test)
6. email-security-pipeline #901

## Ready-to-execute human actions

```bash
# Rebase deferred tracker PR after today's merge wave
gh pr checkout 1036 -R abhimehro/personal-config
git fetch origin main && git merge origin/main
# resolve tasks/todo.md if needed, push, wait for CI
gh pr merge 1036 -R abhimehro/personal-config --squash --delete-branch

# Investigate CodeScene delta on Jules QA shell
gh pr checks 1048 -R abhimehro/personal-config
# fix or close if scratch_triage.py is out of scope

# Human review then merge ONE of the parse_inventory cluster (not both without consolidation)
gh pr view 1039 -R abhimehro/personal-config
gh pr view 1047 -R abhimehro/personal-config
```

## Security gate notes

- Gate 2 **pass** on all merged PRs (no secrets added; CWE-94 binding verified).
- **Never merged:** #1039, #1047 (toolchain trust boundary).
- **Never merged with failing required checks:** #1048 (CodeScene).
