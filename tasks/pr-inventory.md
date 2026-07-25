# PR Inventory — 2026-07-25 (Phase 1)

**Preflight:** PASS 7/7 (`bash scripts/preflight-gh-pr-automation.sh --config tasks/pr-review-agent.config.yaml`)  
**Auth note:** Env `GH_TOKEN` (`github_pat_…`) returned **401 Bad credentials**; session used `unset GH_TOKEN` + `gh` hosts.yml Cursor app token. Merges worked; `gh pr comment` GraphQL `addComment` blocked — reviews posted via Cursor Automation MCP.  
**Mode:** review-and-merge · squash · stale 30d · auto-fix on  
**Branch:** `cursor-agent/pr-workflow-automation-4f4e`

## Summary counts (start of session)

| Repo | Open | In-scope |
|------|-----:|---------:|
| personal-config | 7 | 7 |
| ctrld-sync | 1 | 1 |
| email-security-pipeline | 8 | 8 |
| Seatek_Analysis | 5 | 5 |
| Hydrograph_Versus_Seatek_Sensors_Project | 3 | 3 |
| series_correction_project_updated | 5 | 5 |
| repoprompt-ce | 2 | 2 |
| **Total** | **31** | **31** |

## Inventory table

| Repo | PR | Author | Category | CI | Mergeable | Age | Draft | Title |
|------|---:|--------|----------|----|-----------|----:|:----:|-------|
| personal-config | 1721 | abhimehro | PERFORMANCE | PASS | CONFLICTING | 4 | | Bolt: cache env vars in detect_duplicates.py |
| personal-config | 1748 | abhimehro | CI/INFRA | PASS | CONFLICTING* | 2 | | fix(visual-recap) salvage |
| personal-config | 1766 | abhimehro | SECURITY | PASS | CONFLICTING* | 0 | | fix(ssrf) safe_http |
| personal-config | 1767 | abhimehro | SECURITY | PASS | MERGEABLE | 0 | | security(ABHI-1515) fix_drafts / gh_token_env |
| personal-config | 1768 | abhimehro | CI/INFRA | PASS | MERGEABLE | 0 | | Code Quality: remove test sleeps |
| personal-config | 1769 | abhimehro | SECURITY | PASS | MERGEABLE | 0 | | fix(ABHI-1514) ensure_gh_token |
| personal-config | 1770 | abhimehro | PERFORMANCE | PASS | MERGEABLE | 0 | | Bolt: pre-compile section ID regex |
| ctrld-sync | 1060 | abhimehro | SECURITY | PASS | MERGEABLE | 0 | | Sentinel: exception chaining leak |
| email-security-pipeline | 1319 | abhimehro | PERFORMANCE | PASS | MERGEABLE | 4 | | Bolt: gh_token_cli writes |
| email-security-pipeline | 1324 | abhimehro | PERFORMANCE | PASS | MERGEABLE | 4 | | Bolt: _check_auth_results |
| email-security-pipeline | 1328 | abhimehro | SECURITY | PASS | MERGEABLE | 4 | | Fix TOCTOU config perms |
| email-security-pipeline | 1342 | abhimehro | REFACTOR | PASS | MERGEABLE | 2 | | IMAPClient EmailIngestionConfig |
| email-security-pipeline | 1348 | app/cursor | CI/INFRA | PASS | MERGEABLE | 1 | D→ready | docs(agents) remove stale bug note |
| email-security-pipeline | 1353 | abhimehro | SECURITY | PASS | MERGEABLE | 1 | | Sentinel: TOCTOU file perms |
| email-security-pipeline | 1356 | abhimehro | UI | PASS | MERGEABLE | 0 | | Palette: password typing hint |
| email-security-pipeline | 1359 | abhimehro | PERFORMANCE | PASS | MERGEABLE | 0 | | Bolt: Auth-Results fast-path |
| Seatek_Analysis | 507 | abhimehro | SECURITY | PASS | MERGEABLE | 3 | | Sentinel: subprocess env exfil |
| Seatek_Analysis | 511 | app/devin-ai-integration | SECURITY | FAIL | MERGEABLE | 3 | | Devin path-traversal / modularization |
| Seatek_Analysis | 518 | abhimehro | SECURITY | PASS | MERGEABLE | 2 | | Sentinel: env denylist |
| Seatek_Analysis | 521 | app/dependabot | DEPENDENCY | PASS | MERGEABLE | 1 | | pandas major constraint |
| Seatek_Analysis | 525 | abhimehro | SECURITY | PASS | MERGEABLE | 1 | | Sentinel: env filter order |
| Hydrograph… | 411 | app/cursor | DEPENDENCY | PASS | MERGEABLE | 0 | D→ready | numpy upper bound align |
| Hydrograph… | 413 | abhimehro | SECURITY | FAIL | MERGEABLE | 0 | | Sentinel: device-file DoS |
| Hydrograph… | 414 | abhimehro | PERFORMANCE | PASS | MERGEABLE | 0 | | Bolt: _extract_hydro_years |
| series_correction… | 268 | abhimehro | SECURITY | PASS | MERGEABLE | 4 | | code health: JSON infinite loop |
| series_correction… | 275 | abhimehro | SECURITY | PASS | CONFLICTING | 4 | | auth + DoS JSON |
| series_correction… | 276 | abhimehro | SECURITY | PASS | MERGEABLE | 4 | | DoS whitespace JSON |
| series_correction… | 285 | abhimehro | SECURITY | FAIL | MERGEABLE | 2 | | dummy_todos memory leak |
| series_correction… | 290 | abhimehro | CI/INFRA | PASS | MERGEABLE | 0 | | Daily QA zero-diff |
| repoprompt-ce | 126 | app/dependabot | CI/INFRA | PASS | MERGEABLE | 8 | | download-artifact major tip |
| repoprompt-ce | 127 | app/dependabot | CI/INFRA | PASS | MERGEABLE | 8 | | upload-artifact major tip |

\* Became CONFLICTING after mid-session merges (bolt.md / overlapping salvage).

## Fail checks (start)

| PR | Failing |
|----|---------|
| Seatek #511 | Trunk Merge Queue (main) |
| Hydrograph #413 | CodeScene Code Health Review (main) |
| series_correction #285 | CodeScene Code Health Review (main) |
