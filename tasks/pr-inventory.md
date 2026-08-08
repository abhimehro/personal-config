# PR Inventory — 2026-08-07

Phase 1 cron (13:00 UTC). Preflight PASS 7/7. Auth: `abhimehro` PAT.
Mode: review-and-merge. Stale threshold: 30 days. Merge: squash.

Scope: automation-driven open PRs (bot authors + human-authored
Bolt/Jules/Sentinel/Palette/salvage/cursor-agent/Dependabot).

## Start-of-session counts (auto targets)

| Repo | Auto open |
| ---- | --------: |
| personal-config | 8 |
| ctrld-sync | 6 |
| email-security-pipeline | 4 |
| Seatek_Analysis | 14 |
| Hydrograph… | 10 |
| series_correction… | 4 |
| repoprompt-ce | 12 |
| **Total** | **58** |

## End-of-session open remainder (auto)

| Repo | Open | Notes |
| ---- | ---: | ----- |
| personal-config | 1 | #1907 CORS ESCALATE |
| ctrld-sync | ~4 | Dependabot lock siblings after #1132; mypy major #1136 |
| email-security-pipeline | ~3 | #1421 CONFLICTING; #1444 opencv major; #1437 salvage draft |
| Seatek_Analysis | 10 | Sentinel path/subprocess cluster |
| Hydrograph… | 8 | Sentinel sanitize_filename cluster |
| series_correction… | 4 | #364/#365 auth; #371 CodeScene; #369 salvage |
| repoprompt-ce | 9 | TOCTOU + failing tests/a11y |
| **Approx open auto** | **~44** | |

## Merged this session (24)

| Repo | PR | Category | Note |
| ---- | -- | -------- | ---- |
| ctrld-sync | 1130 | DEPENDENCY | pnpm/action-setup |
| ctrld-sync | 1131 | DEPENDENCY | gh-aw actions/setup pin |
| ctrld-sync | 1129 | DEPENDENCY | gh-aw setup-cli |
| ctrld-sync | 1127 | UI | Palette error grammar |
| ctrld-sync | 1126 | SECURITY | pygments 2.20.0 CVE (verified on main) |
| ctrld-sync | 1123 | CI/INFRA | repo-health |
| ctrld-sync | 1132 | DEPENDENCY | pytest-cov (one lock / 0fb) |
| Seatek_Analysis | 619 | DEPENDENCY | pnpm/action-setup |
| Seatek_Analysis | 618 | CI/INFRA | zero-diff daily QA |
| Seatek_Analysis | 621 | PERFORMANCE | Bolt POSIXct guard (verified on main) |
| Hydrograph… | 481 | DEPENDENCY | pnpm/action-setup |
| Hydrograph… | 482 | DEPENDENCY | pandas requirements align to 3.0.5 (verified) |
| email-security-pipeline | 1439 | UI | Palette email hint |
| email-security-pipeline | 1435 | CI/INFRA | repo-health |
| email-security-pipeline | 1446 | DEPENDENCY | certifi |
| email-security-pipeline | 1445 | DEPENDENCY | pytest |
| email-security-pipeline | 1443 | DEPENDENCY | pre-commit |
| email-security-pipeline | 1442 | CI/INFRA | zero-diff daily QA |
| personal-config | 1924 | PERFORMANCE | Bolt yaml import fallback |
| personal-config | 1931 | CI/INFRA | repo-health TruffleHog |
| personal-config | 1912 | CI/INFRA | docs Phase1 2026-08-04 |
| repoprompt-ce | 209 | CI/INFRA | zero-diff Jules QA |
| repoprompt-ce | 203 | UI | Palette a11y Chat buttons |
| repoprompt-ce | 205 | CI/INFRA | repo-health community templates |

## Closed this session (5)

| Repo | PR | Reason |
| ---- | -- | ------ |
| personal-config | 1925 | CONFLICTING docs cascade after #1912; recovered Aug 5 report |
| personal-config | 1930 | CONFLICTING docs cascade; recovered Aug 6 report |
| personal-config | 1933 | CONFLICTING salvage docs cascade |
| personal-config | 1914 | Trunk MQ fail + docs cascade |
| Seatek_Analysis | 615 | Superseded by focused #621; workflow scope creep |

## Representative remaining (disposition)

| Repo | PR | Disposition |
| ---- | -- | ----------- |
| personal-config | 1907 | ESCALATE CORS |
| Seatek_Analysis | 620/617/612/610/607/605/590/585/580/573 | ESCALATE Sentinel cluster |
| Hydrograph… | 484…459 | ESCALATE sanitize cluster |
| series… | 365/364 | ESCALATE auth |
| series… | 371 | REQUEST_CHANGES + CodeScene trigger |
| series… | 369 | DEFER salvage draft (CodeScene) |
| esp | 1421 | REQUEST_CHANGES / DEFER CONFLICTING |
| esp | 1444 | ESCALATE opencv major |
| esp | 1437 | DEFER salvage draft |
| rpce | 211 | REQUEST_CHANGES XCTSkip (now CONFLICTING) |
| rpce | 210/201/196 | ESCALATE TOCTOU |
| rpce | 212/194/186 | REQUEST_CHANGES failing CI |
| ctrld-sync | 1136 | ESCALATE mypy major |
| ctrld-sync | 1133–1135 | DEFER lock cascade |
