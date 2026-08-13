# PR inventory — 2026-08-13

Phase 1 cron. Preflight PASS 7/7. Age as of 2026-08-13. Status = recommended
disposition (this environment cannot squash-merge or close via `gh`).

| Repo | PR | Author | Category | CI | Conflicts | Age | Status |
| ---- | -- | ------ | -------- | -- | --------- | --- | ------ |
| personal-config | 1985 | abhimehro (Bolt) | PERFORMANCE | green | CLEAN | <1d | HOLD overlap+#1982 yaml skip |
| personal-config | 1984 | abhimehro (Bolt) | PERFORMANCE | green | CLEAN | <1d | APPROVE |
| personal-config | 1982 | abhimehro | CI/INFRA | green | CLEAN | 1d | REQUEST_CHANGES yaml skipIf |
| personal-config | 1980 | abhimehro (Sentinel) | SECURITY | CodeScene fail | UNSTABLE | 1d | ESCALATE + CS trigger |
| personal-config | 1979 | cursor[bot] | CI/INFRA | green | CLEAN | 1d | DEFER salvage draft |
| personal-config | 1978 | abhimehro (Bolt) | PERFORMANCE | green | CLEAN | 1d | HOLD journal prepend |
| personal-config | 1969 | abhimehro | FEATURE | Gitleaks+CodeScene | UNSTABLE | 1d | ESCALATE |
| personal-config | 1907 | abhimehro (Sentinel) | SECURITY | green | CLEAN | 9d | ESCALATE CORS |
| ctrld-sync | 1161 | abhimehro (Bolt) | PERFORMANCE | green | CLEAN | 1d | HOLD 0fo sum pessimization |
| ctrld-sync | 1159 | abhimehro | UI | CodeScene fail | UNSTABLE | 1d | DEFER salvage draft |
| ctrld-sync | 1156 | abhimehro (Sentinel) | SECURITY | green | CLEAN | 3d | ESCALATE + 0fg scratch |
| ctrld-sync | 1136 | dependabot[bot] | DEPENDENCY | green | CLEAN | 6d | ESCALATE mypy 2.x major |
| email-security-pipeline | 1471 | abhimehro | CI/INFRA | green | CLEAN | <1d | APPROVE SHA verified |
| email-security-pipeline | 1469 | abhimehro (Palette) | UI | green | CLEAN | 1d | APPROVE |
| email-security-pipeline | 1444 | dependabot[bot] | DEPENDENCY | pytest+label fail | UNSTABLE | 6d | ESCALATE opencv 5.x |
| Seatek_Analysis | 665 | abhimehro (Sentinel) | SECURITY | green | CLEAN | <1d | ESCALATE |
| Seatek_Analysis | 664 | abhimehro (QA) | CI/INFRA | green | CLEAN | 1d | CLOSE-recommend zero-diff |
| Seatek_Analysis | 662 | abhimehro (Sentinel) | SECURITY | green | CLEAN | 1d | ESCALATE |
| Seatek_Analysis | 661 | dependabot[bot] | DEPENDENCY | validate fail | UNSTABLE | 1d | ESCALATE numpy 1.26→2.5 |
| Seatek_Analysis | 657 | abhimehro (Sentinel) | SECURITY | green | CLEAN | 1d | REQUEST_CHANGES fail-open |
| Seatek_Analysis | 643 | cursor[bot] | CI/INFRA | CodeScene+CodeQL | UNSTABLE | 3d | DEFER + CS trigger |
| Hydrograph… | 509 | dependabot[bot] | DEPENDENCY | green | CLEAN | 1d | APPROVE numpy patch |
| Hydrograph… | 507 | abhimehro | SECURITY | test fail | UNSTABLE | 1d | DEFER salvage draft |
| Hydrograph… | 498 | cursor[bot] | CI/INFRA | test fail | UNSTABLE | 3d | DEFER 0fg junk |
| series_correction… | 390 | abhimehro (Bolt) | PERFORMANCE | green | CLEAN | <1d | REQUEST_CHANGES 0fp |
| series_correction… | 386 | dependabot[bot] | DEPENDENCY | test 3.10 fail | UNSTABLE | 2d | ESCALATE pandas 3.x |
| series_correction… | 385 | dependabot[bot] | DEPENDENCY | test 3.10/3.11 fail | UNSTABLE | 2d | ESCALATE numpy 2.2→2.5 |
| series_correction… | 384 | abhimehro (QA) | CI/INFRA | green | CLEAN | 3d | CLOSE-recommend zero-diff |
| series_correction… | 375 | abhimehro | CI/INFRA | UNSTABLE | UNSTABLE | 5d | DEFER salvage CodeScene |
| repoprompt-ce | 241 | abhimehro (Bolt) | PERFORMANCE | Style fail | UNSTABLE | <1d | DEFER DateFormatter cluster |
| repoprompt-ce | 240 | abhimehro (QA) | CI/INFRA | green | CLEAN | 1d | CLOSE-recommend zero-diff |
| repoprompt-ce | 239 | abhimehro (Sentinel) | SECURITY | Style+tests fail | UNSTABLE | 1d | ESCALATE TOCTOU |
| repoprompt-ce | 237 | abhimehro | CI/INFRA | green | CLEAN | 1d | DEFER salvage draft |
| repoprompt-ce | 236 | abhimehro (Bolt) | PERFORMANCE | shard 3 fail | UNSTABLE | 1d | DEFER DateFormatter cluster |
| repoprompt-ce | 235 | abhimehro (Palette) | UI | green | CLEAN | 1d | APPROVE |
| repoprompt-ce | 234 | abhimehro (QA) | CI/INFRA | shards fail | UNSTABLE | 2d | CLOSE-recommend zero-diff |
| repoprompt-ce | 232 | abhimehro (Sentinel) | SECURITY | green | CLEAN | 2d | ESCALATE huge TOCTOU |
| repoprompt-ce | 231 | abhimehro (Bolt) | PERFORMANCE | tests fail | UNSTABLE | 2d | REQUEST_CHANGES (prior) |
| repoprompt-ce | 228 | abhimehro (Sentinel) | SECURITY | Style fail | UNSTABLE | 3d | ESCALATE huge TOCTOU |
| repoprompt-ce | 227 | abhimehro | CI/INFRA | shard 3 fail | UNSTABLE | 3d | DEFER salvage |
| repoprompt-ce | 226 | abhimehro (Palette) | UI | tests fail | UNSTABLE | 4d | REQUEST_CHANGES scope |

**Counts:** 41 inventoried. Out of scope ordinary-human: none flagged. Salvage drafts: 4.
