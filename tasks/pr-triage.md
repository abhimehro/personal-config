# PR Triage — Phase 2 Salvage 2026-08-12

## Decision summary

| Repo | PR | Disposition | Action |
| ---- | -- | ----------- | ------ |
| Hydrograph… | 504 | SALVAGE | Draft [#507](https://github.com/abhimehro/Hydrograph_Versus_Seatek_Sensors_Project/pull/507); close #504 |
| ctrld-sync | 1150 | SALVAGE | Draft [#1159](https://github.com/abhimehro/ctrld-sync/pull/1159); strip lock/deps; close #1150 |
| repoprompt-ce | 224 | SALVAGE | Draft [#237](https://github.com/abhimehro/repoprompt-ce/pull/237) tests-only (0fj); close #224 |
| series… | 378 | CLOSE no-op | Target `dummy_todos.py` gone from main; no auth re-intro |
| repoprompt-ce | 231 | HOLD/ESCALATE | DateFormatter + contamination (0fm); comment only |
| personal-config | 1977 | DOCS recover | Fold Phase 1 reports into Phase 2 docs PR; close #1977 |
| personal-config | 1907 | ESCALATE | CORS trust boundary — human |
| ctrld-sync | 1156 | ESCALATE | TOCTOU plan JSON — human |
| ctrld-sync | 1136 | ESCALATE | mypy 2.x major — human |
| email-security-pipeline | 1444 | ESCALATE | opencv 5.x + failing CI (S6) |
| Seatek_Analysis | 657 | REQUEST_CHANGES | fail-open OSError→{} |
| Seatek_Analysis | 643 | DEFER | CodeScene/CodeQL |
| Hydrograph… | 498 | DEFER | failing tests + junk |
| series… | 386/385 | ESCALATE | pandas/numpy majors + failing CI |
| series… | 375 | DEFER | CodeScene salvage test |
| repoprompt-ce | 232/228 | ESCALATE | TOCTOU contaminated |
| repoprompt-ce | 226 | REQUEST_CHANGES | a11y scope creep |
| repoprompt-ce | 235/234/227 | DEFER | failing CI / contaminated salvage |

## Human merge priority (drafts)

1. Hydro [#507](https://github.com/abhimehro/Hydrograph_Versus_Seatek_Sensors_Project/pull/507) — sanitize newline tests
2. ctrld [#1159](https://github.com/abhimehro/ctrld-sync/pull/1159) — dry-run pluralize (0fm-compliant `sync_results` count)
3. rpce [#237](https://github.com/abhimehro/repoprompt-ce/pull/237) — REPLInputParserTests (`make dev-test FILTER=REPLInputParserTests`)
4. Prior queue: series [#375](https://github.com/abhimehro/series_correction_project_updated/pull/375), rpce [#227](https://github.com/abhimehro/repoprompt-ce/pull/227) (contaminated — prefer fresh re-roll)

## Rules applied

- S1 no autonomous merges
- 0y journal append-only
- 0fj contaminated salvage → fresh main + unique files
- 0fm dry-run error_count from `sync_results`
- 0fn do not re-apply rejected insecure / do not resurrect deleted auth demos
- 0fk one competing `tasks/*` docs lineage
- 0ew skip `request_reviewers` when author is abhimehro
