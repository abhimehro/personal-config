# PR Triage — 2026-05-20 salvage workflow

**Session:** Automated PR salvage + cleanup (cron). Preflight passed.

## MERGED (squash, branch deleted)

| Repo | PR | Notes |
| --- | ---: | --- |
| email-security-pipeline | 881 | CWE-94 workflow_dispatch injection fix (security-first) |
| email-security-pipeline | 883 | Remove empty JSON artifacts |
| email-security-pipeline | 843 | Fix missing whitespace filenames |
| email-security-pipeline | 820 | Refactor `_analyze_email` complexity |
| ctrld-sync | 825 | mypy fix in `test_ux.py` |
| ctrld-sync | 807 | Simplify `_retry_request` nesting |
| Seatek_Analysis | 199 | Concurrent GitHub fetch (Bolt) |
| Seatek_Analysis | 175 | Extract `execute_tasks_parallel` |
| series_correction_project_updated | 53 | Remove redundant `pd.Series` wrapping |

## CLOSED-SUPERSEDED

| Repo | PR | Reason |
| --- | ---: | --- |
| personal-config | 986, 987, 988 | Conflicted batch2 Sentinel salvages; superseded by draft **#1005** (v2 from `main`) |
| ctrld-sync | 824 | Overlapping hostname dedup; prefer **#822** or **#830** |
| email-security-pipeline | 874 | Duplicate Palette UX vs salvage **#867** |

## SALVAGE-DRAFT (human merge required)

| Repo | PR | Tier | Notes |
| --- | ---: | --- | --- |
| personal-config | 1005 | T1 | CWE-78 mole core — rebuilt `cursor-agent/salvage-pc-923-v2-20260520` |

## DEFER — CONFLICTING (needs v2 salvage from `main`)

### personal-config (batch2, `update-branch` → 422)

983, 985, 990–993, 995–998, 1000 — hot files moved on `main` (#989, #994, #999, #1002, #1004). Rebuild per intent lane; do not `git checkout pr --` on journals.

### Seatek_Analysis

188–198 — salvage batch1 branches DIRTY after #199/#175 merges.

### email-security-pipeline

867 — Palette salvage; DIRTY after #881 merge.

### ctrld-sync

841, 823, 807 (merged), overlapping dedup queue: 788, 820, 822, 830.

## DEFER — UNSTABLE CI (do not merge)

| Repo | PR | Blocker |
| --- | ---: | --- |
| ctrld-sync | 830 | `benchmark` failing |
| ctrld-sync | 822, 821, 820, 818, 815 | CodeScene / overlapping dedup — pick one canonical PR |
| Seatek_Analysis | 172, 189 | UNSTABLE rollup |
| email-security-pipeline | 844, 842, 841, 823, 807 | conflicts or UNSTABLE |

## READY (CLEAN, not merged this session)

_None remaining after merge pass._

## Hydrograph_Versus_Seatek_Sensors_Project

No open in-scope PRs.
