# PR Triage — 2026-06-03

**Mode:** review-and-merge | **Stale threshold:** 30 days | **Merge:** squash

## Phase 1 disposition summary

| Disposition | Count | Notes |
| --- | ---: | --- |
| MERGE | 25 | All required checks green at merge time |
| CLOSE-DUPLICATE | 5 | Seatek overlapping test/health PRs |
| CLOSE-SUPERSEDED | 2 | #1028 zero-diff; #244 after #256 |
| CLOSE (zero-diff) | 1 | Included in superseded row |
| ESCALATE | 6 | ESP production + draft security |
| DEFER | 2 | Hydrograph #224 CodeScene; #223 conflicts |
| DEFER (draft) | 3 | personal-config session artifact PRs |

## Per-PR disposition (open tail)

| Repo | PR | Disposition | Rationale |
| --- | ---: | --- | --- |
| personal-config | 1155 | DEFER | Draft; touches `tasks/*` automation artifacts |
| personal-config | 1154 | DEFER | Draft salvage; UNSTABLE CI |
| personal-config | 1151 | DEFER | Draft; DIRTY conflict on `tasks/*` |
| email-security-pipeline | 1024 | ESCALATE | Sentinel; 17 files incl. `main.py`, ingestion |
| email-security-pipeline | 1023 | ESCALATE | `nlp_analyzer.py` production change |
| email-security-pipeline | 1022 | ESCALATE | `main.py` refactor (CONFLICTING) |
| email-security-pipeline | 1021 | ESCALATE | `app_runner.py` secure-file refactor |
| email-security-pipeline | 1008 | ESCALATE | Draft T1 Zip Slip salvage |
| email-security-pipeline | 1006 | ESCALATE | Workflow consolidation + bandit history |
| Seatek_Analysis | 249 | MERGE-AFTER-FIX | CONFLICTING after merge burst; rebase needed |
| Seatek_Analysis | 247 | MERGE-AFTER-FIX | CONFLICTING; overlaps closed #243 |
| Hydrograph | 224 | DEFER | CodeScene fail; other checks pass |
| Hydrograph | 223 | MERGE-AFTER-FIX | DIRTY after #218–#222 merges |

## Duplicate groups resolved

| Keeper | Closed duplicates | Overlap |
| --- | --- | --- |
| #253 | #252 | `test-write_year_sheet.R` |
| #249 | #248 | `test-clean_vals.R` |
| #255 | #246 | `test-execute_tasks_parallel.R` |
| #245 | #242 | `scan_file` removal |
| #256 (merged) | #244 | `get_repo_info` |

## Ready-to-Execute Human Actions

### Rebase-and-merge (after `git fetch` / `gh pr checkout`)

```bash
# Seatek — conflicted test/health PRs
gh pr checkout 249 --repo abhimehro/Seatek_Analysis && git fetch origin main && git merge origin/main
# resolve, push, then:
gh pr merge 249 --repo abhimehro/Seatek_Analysis --squash --delete-branch

gh pr checkout 247 --repo abhimehro/Seatek_Analysis && git fetch origin main && git merge origin/main
# resolve, push, then:
gh pr merge 247 --repo abhimehro/Seatek_Analysis --squash --delete-branch

# Hydrograph — Bolt data_loader
gh pr checkout 223 --repo abhimehro/Hydrograph_Versus_Seatek_Sensors_Project && git fetch origin main && git merge origin/main
gh pr merge 223 --repo abhimehro/Hydrograph_Versus_Seatek_Sensors_Project --squash --delete-branch
```

### Human security review (email-security-pipeline)

Review and merge in order: **#1008** (T1 Zip Slip draft) → **#1021** → **#1023** → **#1024** / **#1022** (resolve conflicts). Close **#1006** if superseded by workflow on `main`.

### Draft session artifacts (personal-config)

Merge or close **#1155**, **#1154**, **#1151** after reconciling `tasks/pr-*.md` conflicts manually.
