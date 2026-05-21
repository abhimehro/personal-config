# PR Triage — 2026-05-21 salvage workflow

**Session:** Automated PR salvage + cleanup (cron `0 17 * * *`).  
**Preflight:** passed (six repos, read-only).

## MERGED (squash, branch deleted) — this session

| Repo | PR | Notes |
| --- | ---: | --- |
| email-security-pipeline | 886 | QA format fixes (daily review); identical files to closed #885 |
| Seatek_Analysis | 202 | Bolt: optimize relative path in hot loop |
| personal-config | 1009 | Bolt: ThreadPoolExecutor for `parse_inventory` gh API calls |

## CLOSED-DUPLICATE — this session

| Repo | PR | Reason |
| --- | ---: | --- |
| email-security-pipeline | 885 | Same changed files as #886 (`QA_SUMMARY.md`, `alert_system.py`, `email_parser.py`) |

## MERGED (prior session, verified live)

| Repo | PR | Notes |
| --- | ---: | --- |
| personal-config | 1005 | T1 CWE-78 mole core salvage — no longer open |

## ESCALATE (human action)

| Repo | PR | Tier | Reason |
| --- | ---: | --- | --- |
| series_correction_project_updated | 55 | T1 | Sentinel exception leakage fix; CodeScene failing |
| email-security-pipeline | 887 | T2 | Draft workflow change (`greetings.yml`); mark ready + review before merge |

## DEFER — CONFLICTING (v2 salvage from `main`, do not `update-branch`)

### personal-config

| PR | Salvages | Notes |
| ---: | --- | --- |
| 985 | #938 | Secrets path; DIRTY + failing checks; #1005 landed overlapping mole hardening |
| 992 | #945 | `scratch_triage` tests |
| 995 | #939 | Tracker parallel I/O |

### email-security-pipeline

867 (Palette #861), 841, 823, 807 — DIRTY after security/merge cascade on `main`.

### Seatek_Analysis

188–198 — salvage batch1 DIRTY after #199, #175, **#202** merges.

## DEFER — UNSTABLE CI (do not merge)

| Repo | PRs | Blocker |
| --- | --- | --- |
| ctrld-sync | 821, 818, 815, 789 | CodeScene Code Health Review |
| Seatek_Analysis | 189, 172 | Pending/failing required checks |
| email-security-pipeline | 844, 842 | Jules PRs UNSTABLE |

## READY (CLEAN, not merged)

| Repo | PR | Notes |
| --- | ---: | --- |
| personal-config | 1011 | Session artifacts on `cursor-agent/automated-pr-workflow-4420` — merge after this commit lands |

## Hydrograph_Versus_Seatek_Sensors_Project

No open in-scope PRs.

## Phase 2 next actions (ordered)

1. Human: merge **series_correction#55** if CodeScene waiver acceptable; else fix CodeScene findings on branch.
2. Human: review **email-security-pipeline#887** (mark draft ready → merge if greetings change is intended).
3. Agent/human: close **personal-config#985** as superseded-by-#1005 if diff intent fully covered; else open `cursor-agent/salvage-pc-938-v2-20260521` draft.
4. Rebuild remaining batch1/batch2 salvage branches from fresh `main` per `docs/automated-pr-salvage-agent.md` (never `update-branch` after burst merges — Lesson 0cc).
