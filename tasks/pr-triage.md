# PR Triage — 2026-05-29

## Duplicate / overlap

None. Each open PR targets distinct intent (SHA pin QA vs Bolt parallel gh vs ESP bandit nosec vs MAD vectorization).

## Superseded / zero-diff

None at inventory time.

## Stale (>30 days)

None.

## Infra cascade (Lesson 0t / 0u)

**personal-config — label workflow:** `pull_request_target` runs workflow from `main`. Until #1087 merged, `actions/labeler@v6.1.0` failed org SHA-pin policy. **Resolution:** merged #1087 first (infra fix), then autofixed #1086 merge conflicts with main.

**email-security-pipeline — pytest/bandit/label:** Jobs fail at setup because workflows reference unpinned `actions/checkout@v6` / `actions/setup-python@v6`. Not caused by PR #956 diff (nosec only). **Resolution:** escalate; needs repo-wide workflow SHA pin PR (salvage).

## Ordering applied

1. Merge personal-config #1087 (unblocks labeler on main).
2. Autofix + rebase personal-config #1086.
3. Merge series_correction #84 (security analyzers green; CodeScene infra error).
4. Escalate email-security #956 (trust boundary + CI infra).

## Per-PR disposition

| PR | Disposition | Rationale |
| --- | --- | --- |
| personal-config #1087 | MERGE | CI/INFRA SHA pins; security gates pass; label fail pre-merge was main-side |
| personal-config #1086 | **MERGED** | Autofix conflict resolution; label green after #1087 |
| email-security-pipeline #956 | ESCALATE | `.github/scripts/repository_automation_common.py` + unpinned workflow actions on main |
| series_correction #84 | MERGE | PERFORMANCE; Gate 2 pass; CodeScene delta-error treated as non-blocking infra |
