# PR Inventory — 2026-06-23

**Session:** Automated PR review-and-merge (cron)  
**Preflight:** PASS 6/6 configured repos  
**Mode:** review-and-merge (squash)  
**Stale threshold:** 30 days

## Summary

| Repo | Open (in-scope) | Merged this session | Closed | Remainder |
|------|-----------------|---------------------|--------|-----------|
| personal-config | 10 | 1 (#1331) | 0 | 10 |
| ctrld-sync | 7 | 0 | 0 | 7 |
| email-security-pipeline | 0 | 3 | 0 | **0** |
| Seatek_Analysis | 1 | 7 | 0 | 1 |
| Hydrograph_Versus_Seatek_Sensors_Project | 0 | 3 | 1 (#290) | **0** |
| series_correction_project_updated | 1 | 1 | 1 (#142) | 1 |
| repoprompt-ce | 13 | 0 | 0 | 13 |

## Inventory (post-session remainder)

| Repo | PR | Author | Category | CI | Conflicts | Age (d) | Status |
|------|-----|--------|----------|-----|-----------|---------|--------|
| personal-config | [#1337](https://github.com/abhimehro/personal-config/pull/1337) | abhimehro | PERFORMANCE | FAIL (Codacy) | MERGEABLE | 0 | DEFER |
| personal-config | [#1336](https://github.com/abhimehro/personal-config/pull/1336) | abhimehro | PERFORMANCE | FAIL (Codacy) | MERGEABLE | 0 | DEFER |
| personal-config | [#1334](https://github.com/abhimehro/personal-config/pull/1334) | abhimehro | CI/INFRA | FAIL (Codacy) | MERGEABLE | 0 | ESCALATE |
| personal-config | [#1333](https://github.com/abhimehro/personal-config/pull/1333) | dependabot | DEPENDENCY | FAIL (Codacy) | MERGEABLE | 0 | DEFER |
| personal-config | [#1332](https://github.com/abhimehro/personal-config/pull/1332) | dependabot | DEPENDENCY | FAIL (Codacy) | MERGEABLE | 0 | DEFER |
| personal-config | [#1330](https://github.com/abhimehro/personal-config/pull/1330) | dependabot | DEPENDENCY | FAIL (Codacy) | MERGEABLE | 0 | DEFER |
| personal-config | [#1329](https://github.com/abhimehro/personal-config/pull/1329) | abhimehro | UI | FAIL (Codacy) | MERGEABLE | 0 | DEFER |
| personal-config | [#1326](https://github.com/abhimehro/personal-config/pull/1326) | abhimehro | UI | FAIL (Codacy) | MERGEABLE | 0 | DEFER |
| personal-config | [#1325](https://github.com/abhimehro/personal-config/pull/1325) | cursor | CI/INFRA | FAIL (Codacy) | MERGEABLE | 0 | DEFER (draft) |
| personal-config | [#1324](https://github.com/abhimehro/personal-config/pull/1324) | cursor | CI/INFRA | FAIL (Codacy) | MERGEABLE | 1 | DEFER (draft) |
| ctrld-sync | [#943](https://github.com/abhimehro/ctrld-sync/pull/943) | abhimehro | REFACTOR | FAIL (CodeScene) | MERGEABLE | 0 | DEFER (cs-agent posted) |
| ctrld-sync | [#942–938](https://github.com/abhimehro/ctrld-sync/pull/942) | dependabot | DEPENDENCY | FAIL (mypy/ruff) | MERGEABLE | 0 | DEFER (blocked by #943) |
| ctrld-sync | [#936](https://github.com/abhimehro/ctrld-sync/pull/936) | cursor | REFACTOR | FAIL (mypy) | MERGEABLE | 0 | DEFER (draft) |
| Seatek_Analysis | [#351](https://github.com/abhimehro/Seatek_Analysis/pull/351) | dependabot | DEPENDENCY | FAIL (validate) | MERGEABLE | 0 | DEFER |
| series_correction_project_updated | [#144](https://github.com/abhimehro/series_correction_project_updated/pull/144) | abhimehro | REFACTOR | PENDING | MERGEABLE | 0 | DEFER (cs-agent posted) |
| repoprompt-ce | [#49](https://github.com/abhimehro/repoprompt-ce/pull/49) | abhimehro | PERFORMANCE | FAIL (Style) | MERGEABLE | 0 | DEFER |
| repoprompt-ce | [#48](https://github.com/abhimehro/repoprompt-ce/pull/48) | abhimehro | UI | FAIL | MERGEABLE | 0 | DEFER |
| repoprompt-ce | [#47](https://github.com/abhimehro/repoprompt-ce/pull/47) | abhimehro | REFACTOR | FAIL | MERGEABLE | 0 | DEFER |
| repoprompt-ce | [#46–42](https://github.com/abhimehro/repoprompt-ce/pull/46) | dependabot | DEPENDENCY | FAIL (Style) | MERGEABLE | 0 | DEFER |
| repoprompt-ce | [#41](https://github.com/abhimehro/repoprompt-ce/pull/41) | abhimehro | SECURITY | FAIL | MERGEABLE | 0 | ESCALATE (draft salvage) |
| repoprompt-ce | [#39](https://github.com/abhimehro/repoprompt-ce/pull/39) | abhimehro | PERFORMANCE | FAIL (Style) | MERGEABLE | 1 | DEFER |
| repoprompt-ce | [#25](https://github.com/abhimehro/repoprompt-ce/pull/25) | abhimehro | UI | FAIL (Style) | MERGEABLE | 2 | DEFER (salvage) |
| repoprompt-ce | [#24](https://github.com/abhimehro/repoprompt-ce/pull/24) | abhimehro | REFACTOR | FAIL (Style) | MERGEABLE | 2 | DEFER (salvage) |

## Merged this session

| Repo | PR | Title |
|------|-----|-------|
| personal-config | #1331 | codacy/codacy-analysis-cli-action 1.1.0 → 4.4.7 |
| email-security-pipeline | #1143 | ruby/setup-ruby 1.313.0 → 1.314.0 |
| email-security-pipeline | #1142 | github/gh-aw 0.80.5 → 0.80.9 |
| email-security-pipeline | #1140 | Palette error message visual separation |
| Seatek_Analysis | #355, #354, #353, #352, #350, #358, #357 | deps + Bolt + Sentinel |
| Hydrograph_Versus_Seatek_Sensors_Project | #287, #289, #291 | dep + QA + Bolt np.where |
| series_correction_project_updated | #145 | Bolt vectorize Z-score |

## Closed this session

| Repo | PR | Reason |
|------|-----|--------|
| Hydrograph_Versus_Seatek_Sensors_Project | #290 | Duplicate/superseded by merged #291 |
| series_correction_project_updated | #142 | Duplicate/superseded by merged #145 |
