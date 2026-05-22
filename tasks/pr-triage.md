# Automated PR triage — 2026-05-22

**Mode:** review-and-merge (live)  
**Stale threshold:** 30 days — none of the open queue exceeded threshold this run.

## Phase 1 dispositions

| Disposition | Count | PRs |
| --- | ---: | --- |
| MERGE (executed) | 8 | personal-config **#1015, #1012, #1014, #1018**; email-security-pipeline **#889**; Hydrograph **#195**; Seatek_Analysis **#189**; series_correction **#56**; personal-config **#1011** |
| CLOSE-SUPERSEDED | 1 | personal-config **#1013** (overlapped merged #1011 session docs) |
| ESCALATE | 3 | personal-config **#1017** (dummy.md + automation toolchain); email-security-pipeline **#887** (unpinned action tag); personal-config **#985** (security path + failing tests) |
| DEFER-CONFLICT | 14 | personal-config **#995, #992**; email-security-pipeline **#867, #841, #823, #807**; Seatek_Analysis **#198–#188** (salvage batch) |
| DEFER-CI | 9 | ctrld-sync **#821, #818, #815, #789**; email-security-pipeline **#844, #842**; Seatek_Analysis **#172**; series_correction **#55** |

## Duplicate / overlap notes

- **personal-config #1013 vs #1011:** Same class of session artifact updates under `tasks/`; #1011 merged first → **#1013 closed**.
- **Seatek_Analysis salvage batch (#198–#188):** Overlapping Bolt micro-optimizations on `Updated_Seatek_Analysis.R` / scanner paths; all **CONFLICTING** after #189 merge — route to Salvage Agent v2 branches (Lesson 0ed).
- **ctrld-sync salvage (#821, #818, #815):** Non-overlapping files but shared failing optional/required checks — defer as a repo group until CodeScene/greeting/mypy green.

## Ready-to-execute human actions

None queued for merge this session (remaining tails are DEFER or ESCALATE). Next salvage cycle should:

1. Rebuild v2 salvage branches from `origin/main` for personal-config batch2 (**#985–#995**).
2. Fix or waive **CodeScene** on ctrld-sync / series_correction **#55** before merge.
3. Re-pin **email-security-pipeline #887** to digest SHA or close in favor of Dependabot.

## Security escalations (do not auto-merge)

| Repo | PR | Reason |
| --- | ---: | --- |
| personal-config | 1017 | Trust boundary: `scratch_inventory.py` / `scratch_triage.py`; hygiene: `dummy.md` |
| personal-config | 985 | Trust boundary: hardcoded secrets path + failing `Run All Tests` |
| email-security-pipeline | 887 | Supply chain: floating `actions/first-interaction@v3.1.0` vs pinned SHA |
| series_correction_project_updated | 55 | Exception leakage in batch processing — review + CodeScene |
