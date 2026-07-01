# PR Triage — 2026-07-01

**Session:** cron `0 17 * * *` salvage & cleanup  
**Input:** Live GitHub re-fetch + `tasks/pr-review-2026-06-30.md` deferred tail

## Triage matrix

| Repo | PR | Author | Merge state | CI | Disposition | Rationale |
|------|-----|--------|-------------|-----|-------------|-----------|
| personal-config | #1443 | abhimehro | CLEAN | green | **MERGE** | Workflow consolidation; all gates pass |
| personal-config | #1447 | cursor | DIRTY | n/a | **CLOSE** | Session-doc draft; supersede with dated run |
| personal-config | #1446 | abhimehro | DIRTY | n/a | **SALVAGE** → #1448 | ps aux awk optimization |
| personal-config | #1442 | abhimehro | DIRTY | n/a | **SALVAGE** → #1449 | Test-only format/coverage |
| personal-config | #1434 | abhimehro | UNSTABLE | fail tests | **SALVAGE** → #1450 | Adapt get_duplicates test to run_gh API |
| personal-config | #1438 | abhimehro | DIRTY | n/a | **SALVAGE** → #1451 | allowlist mocks test file only |
| email-security-pipeline | #1195 | abhimehro | CLEAN | green | **MERGE** | Code scanning permissions fix |
| email-security-pipeline | #1200 | abhimehro | DIRTY | n/a | **SALVAGE** → #1202 | T1 URL redaction perf |
| email-security-pipeline | #1178 | abhimehro | DIRTY | n/a | **SALVAGE** → #1203 | IMAP SIZE regex |
| email-security-pipeline | #1179 | abhimehro | DIRTY | n/a | **SALVAGE** → #1204 | setup_wizard tests only |
| email-security-pipeline | #1190 | abhimehro | DIRTY | n/a | **DEFER** | Stale Daily QA (28 files, March date) |
| ctrld-sync | #965 | abhimehro | UNSTABLE | CodeScene fail | **DEFER** | cs-agent posted |
| series_correction_project_updated | #166 | abhimehro | UNSTABLE | CodeScene fail | **DEFER** | cs-agent posted |

## Disposition counts

| Disposition | Count |
|-------------|-------|
| MERGE | 2 |
| CLOSE (superseded) | 1 |
| SALVAGE (new draft) | 7 |
| CLOSE (superseded original) | 7 |
| DEFER | 3 |

## Patterns applied

1. **Merge-burst DIRTY cascade** — 7 conflicted originals from post-2026-06-30 merges; salvage-from-main with file-scoped checkout (not wholesale branch merge).
2. **Test API adaptation (Lesson 0z)** — #1434 salvage rewrote mocks from `fetch_pr_info` to `run_gh` to match current `detect_duplicates.py`.
3. **Journal append-only (S2)** — bolt.md entries appended by title dedup, never `git checkout pr -- .jules/bolt.md`.
4. **Session-doc hygiene** — #1447 closed; artifacts live on `cursor-agent/pr-salvage-and-cleanup-2628` only.

## open_followups

```yaml
- repo: abhimehro/personal-config
  pr: 1448-1451
  reason: DRAFT-SALVAGE — human review required
- repo: abhimehro/ctrld-sync
  pr: 965
  reason: DEFER — CodeScene fail; cs-agent posted
- repo: abhimehro/email-security-pipeline
  pr: 1190
  reason: DEFER — stale Daily QA DIRTY
- repo: abhimehro/email-security-pipeline
  pr: 1202-1204
  reason: DRAFT-SALVAGE — security-classified repo
- repo: abhimehro/series_correction_project_updated
  pr: 166
  reason: DEFER — CodeScene fail; cs-agent posted
```
