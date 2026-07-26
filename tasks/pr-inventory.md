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
# PR Inventory — 2026-07-25 (Phase 2 live re-fetch)

**Preflight:** PASS 7/7 (+ `make cursor-cloud-hooks`)  
**Auth:** Env `GH_TOKEN` invalid/empty this session; used `unset GH_TOKEN` + `gh` hosts.yml Cursor app token. App can **push** branches and **list/read** PRs; GraphQL `createPullRequest` / `addComment` / `close` → `Resource not accessible by integration`. Reviews via Cursor Automation MCP; salvage draft PR open blocked — compare URL provided.  
**Mode:** Phase 2 salvage (never autonomous merge)  
**Agent branch:** `cursor-agent/automated-pr-salvage-a2fb`  
**Input:** Phase 1 `tasks/pr-review-2026-07-25.md` (#1771) remainder + live re-fetch

## Live open counts (EOD Phase 2)

| Repo | Open | Notes |
|------|-----:|-------|
| personal-config | 6 | +draft #1771 Phase 1 docs; salvage branch pushed for #1748 |
| ctrld-sync | 1 | #1060 Sentinel |
| email-security-pipeline | 7 | +Jules #1360 zero-diff (close candidate) |
| Seatek_Analysis | 5 | Sentinel siblings + pandas + Devin |
| Hydrograph… | 1 | #413 Sentinel + CodeScene FAIL |
| series_correction… | 4 | dummy_todos cluster |
| repoprompt-ce | 2 | tip artifact majors CONFLICTING |
| **Total** | **26** | |

## Inventory (open, post Phase 1 merges)

| Repo | PR | Author | Category | CI | Mergeable | Draft | Title |
|------|---:|--------|----------|----|-----------|:----:|-------|
| personal-config | 1771 | app/cursor | DOCS | — | CLEAN | D | Phase 1 session 2026-07-25 |
| personal-config | 1769 | abhimehro | SECURITY | PASS | CLEAN | | ensure_gh_token / env-file parser |
| personal-config | 1767 | abhimehro | SECURITY | PASS | CLEAN | | fix_drafts source removal |
| personal-config | 1766 | abhimehro | SECURITY | PASS | CLEAN | | SSRF safe_http (was CONFLICTING @ Phase 1; now clean) |
| personal-config | 1748 | abhimehro | CI/INFRA | PASS | CONFLICTING | | visual-recap salvage (journal conflict only) |
| personal-config | 1721 | abhimehro | PERFORMANCE | PASS | CONFLICTING | | Bolt GH_TOKEN env cache |
| ctrld-sync | 1060 | abhimehro | SECURITY | PASS | CLEAN | | Sentinel exception chaining |
| email-security-pipeline | 1360 | abhimehro | CI/INFRA | — | CLEAN | | Jules Daily QA (0/0/0 files) |
| email-security-pipeline | 1359 | abhimehro | PERFORMANCE | PASS | CLEAN | | Bolt Auth-Results fast-path |
| email-security-pipeline | 1353 | abhimehro | SECURITY | PASS | CLEAN | | Sentinel TOCTOU |
| email-security-pipeline | 1342 | abhimehro | REFACTOR | PASS | CLEAN | | IMAPClient config salvage |
| email-security-pipeline | 1328 | abhimehro | SECURITY | PASS | CLEAN | | TOCTOU config perms |
| email-security-pipeline | 1324 | abhimehro | PERFORMANCE | PASS | CLEAN | | Bolt Auth-Results |
| email-security-pipeline | 1319 | abhimehro | PERFORMANCE | PASS | CLEAN | | Bolt gh_token_cli |
| Seatek_Analysis | 525 | abhimehro | SECURITY | PASS | CLEAN | | Sentinel env filter order |
| Seatek_Analysis | 521 | app/dependabot | DEPENDENCY | PASS | CLEAN | | pandas major |
| Seatek_Analysis | 518 | abhimehro | SECURITY | PASS | CLEAN | | Sentinel env denylist |
| Seatek_Analysis | 511 | app/devin-ai-integration | SECURITY | FAIL | UNSTABLE | | Devin modularization |
| Seatek_Analysis | 507 | abhimehro | SECURITY | PASS | CLEAN | | Sentinel subprocess env |
| Hydrograph… | 413 | abhimehro | SECURITY | FAIL | CLEAN* | | Sentinel device-file DoS (*CodeScene FAIL) |
| series_correction… | 285 | abhimehro | SECURITY | FAIL | UNSTABLE | | dummy_todos memory leak |
| series_correction… | 276 | abhimehro | SECURITY | PASS | CLEAN | | DoS whitespace JSON |
| series_correction… | 275 | abhimehro | SECURITY | PASS | CONFLICTING | | auth + DoS JSON |
| series_correction… | 268 | abhimehro | SECURITY | PASS | CLEAN | | JSON infinite loop |
| repoprompt-ce | 127 | app/dependabot | CI/INFRA | PASS | CONFLICTING | | upload-artifact tip major |
| repoprompt-ce | 126 | app/dependabot | CI/INFRA | PASS | CONFLICTING | | download-artifact tip major |

## Salvage branch prepared (PR create blocked for app token)

| Source PR | Branch | SHA | Compare |
|-----------|--------|-----|---------|
| pc #1748 | `cursor-agent/salvage-pc-1748-visual-recap-v2-a2fb` | `a2208a73` | [open draft](https://github.com/abhimehro/personal-config/compare/main...cursor-agent/salvage-pc-1748-visual-recap-v2-a2fb?quick_pull=1) |

## Fail checks still open

| PR | Failing |
|----|---------|
| Seatek #511 | Trunk Merge Queue |
| Hydrograph #413 | CodeScene Code Health Review (`/cs-agent` already posted) |
| series_correction #285 | CodeScene Code Health Review |
| rpce #126/#127 | merge CONFLICTING (not CI red) |
