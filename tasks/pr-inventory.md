# PR Inventory — 2026-06-13

**Session:** Automated PR review (cron `0 13 * * *`)  
**Preflight:** PASS (6/6 config repos)  
**Mode:** review-and-merge

## Summary

| Repo | Open (start) | Open (end) | Merged | Closed | Deferred |
| --- | ---: | ---: | ---: | ---: | ---: |
| personal-config | 7 | 4 | 2 | 1 | 4 |
| ctrld-sync | 4 | 2 | 2 | 0 | 2 |
| email-security-pipeline | 17 | 2 | 15 | 2 | 2 |
| Seatek_Analysis | 9 | 4 | 3 | 1 | 4 |
| Hydrograph_Versus_Seatek_Sensors_Project | 2 | 1 | 1 | 0 | 1 |
| series_correction_project_updated | 3 | 1 | 2 | 0 | 1 |
| repoprompt-ce | 1 | 0 | 1 | 0 | 0 |
| **Total** | **43** | **14** | **26** | **4** | **14** |

## Remaining open PRs (post-session)

| Repo | PR | Author | Merge | CI | Category | Disposition |
| --- | ---: | --- | --- | --- | --- | --- |
| personal-config | 1235 | abhimehro | MERGEABLE | FAIL tests | PERFORMANCE | DEFER |
| personal-config | 1234 | abhimehro | MERGEABLE | FAIL tests | UI | DEFER |
| personal-config | 1230 | abhimehro | MERGEABLE | FAIL tests | UI | DEFER |
| personal-config | 1231 | app/cursor | MERGEABLE (draft) | FAIL CodeScene | CI/INFRA | **ESCALATE** |
| ctrld-sync | 892 | abhimehro | MERGEABLE | FAIL benchmark+CodeScene | PERFORMANCE | DEFER |
| ctrld-sync | 886 | abhimehro | CONFLICTING | green | UI | DEFER → salvage |
| email-security-pipeline | 1103 | abhimehro | CONFLICTING | FAIL CodeScene | PERFORMANCE | DEFER → salvage |
| email-security-pipeline | 1096 | abhimehro | CONFLICTING | green | REFACTOR | DEFER → salvage |
| Seatek_Analysis | 283 | abhimehro | CONFLICTING | green | SECURITY | Phase 2 salvage |
| Seatek_Analysis | 282 | abhimehro | CONFLICTING | green | PERFORMANCE | Phase 2 salvage |
| Seatek_Analysis | 278 | abhimehro | CONFLICTING | green | PERFORMANCE | Phase 2 salvage |
| Seatek_Analysis | 261 | abhimehro | CONFLICTING | green | PERFORMANCE | Phase 2 salvage |
| Hydrograph_Versus_Seatek_Sensors_Project | 257 | abhimehro | MERGEABLE | FAIL CodeScene | UI | DEFER |
| series_correction_project_updated | 114 | abhimehro | MERGEABLE | FAIL CodeScene | PERFORMANCE | DEFER |

_Generated via `./scripts/get_prs.sh --config tasks/pr-review-agent.config.yaml` after merge burst._
