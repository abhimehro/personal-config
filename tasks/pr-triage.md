# PR Triage — Phase 2 Salvage — 2026-07-16

## Decision summary

| Disposition | Count |
|-------------|------:|
| CLOSE-SUPERSEDED / NO-OP | 6 |
| SALVAGE (new draft) | 11 |
| ESCALATE (unchanged open) | 5 |
| DEFER-CODESCENE | 2 |
| AUTO-RESOLVED → Phase 1 | 3 |
| Session-doc fold | 1 (#1659) |

## CLOSE-SUPERSEDED / NO-OP

| Repo | PR | Reason |
|------|-----|--------|
| personal-config | [#1627](https://github.com/abhimehro/personal-config/pull/1627) | Empty-list UX on main via #1622 |
| personal-config | [#1645](https://github.com/abhimehro/personal-config/pull/1645) | Generator on main via #1644 |
| personal-config | [#1656](https://github.com/abhimehro/personal-config/pull/1656) | Same as #1644 |
| personal-config | [#1649](https://github.com/abhimehro/personal-config/pull/1649) | Import cleanup on main; sequential rewrite would regress |
| Seatek_Analysis | [#473](https://github.com/abhimehro/Seatek_Analysis/pull/473) | Dead imports already gone |
| email-security-pipeline | [#1276](https://github.com/abhimehro/email-security-pipeline/pull/1276) | Zero-diff chore |

## SALVAGE drafts opened (all `--draft`)

| Tier | New PR | Salvages | Notes |
|------|--------|----------|-------|
| T3 | [pc #1661](https://github.com/abhimehro/personal-config/pull/1661) | #1637 #1638 #1654 | Adblock test cluster |
| T3 | [pc #1662](https://github.com/abhimehro/personal-config/pull/1662) | #1642 #1646 #1647 | Automation task tests |
| T3 | [pc #1663](https://github.com/abhimehro/personal-config/pull/1663) | #1636 | Allowlist file tests |
| T3 | [pc #1664](https://github.com/abhimehro/personal-config/pull/1664) | #1623 | Selective tuple fallbacks |
| T3 | [seatek #478](https://github.com/abhimehro/Seatek_Analysis/pull/478) | #476 | rollmean3/tail |
| T3 | [esp #1287](https://github.com/abhimehro/email-security-pipeline/pull/1287) | #1279 | Size boundary tests |
| T3 | [esp #1288](https://github.com/abhimehro/email-security-pipeline/pull/1288) | #1278 | EnvParseError test |
| T3 | [esp #1289](https://github.com/abhimehro/email-security-pipeline/pull/1289) | #1284 | Setup wizard helpers |
| T3 | [hg #378](https://github.com/abhimehro/Hydrograph_Versus_Seatek_Sensors_Project/pull/378) | #376 | Pandas aggregations (fixed dup staticmethod) |
| T3 | [sc #239](https://github.com/abhimehro/series_correction_project_updated/pull/239) | #235 | Integer column rename |
| T3 | [sc #240](https://github.com/abhimehro/series_correction_project_updated/pull/240) | #238 | Sliding-window median |

## ESCALATE (human required — no salvage)

| Tier | PR | Blocker |
|------|-----|---------|
| T1 | [sc #233](https://github.com/abhimehro/series_correction_project_updated/pull/233) | Auth/password hashing |
| T1 | [sc #237](https://github.com/abhimehro/series_correction_project_updated/pull/237) | Paired with #233 |
| T1 | [esp #1267](https://github.com/abhimehro/email-security-pipeline/pull/1267) | GitGuardian FAIL |
| T1 | [seatek #472](https://github.com/abhimehro/Seatek_Analysis/pull/472) | Path hijack still PATH-trusting |
| T2 | [pc #1629](https://github.com/abhimehro/personal-config/pull/1629) | Snyk hooks + conflict |

## DEFER-CODESCENE

| PR | Notes |
|----|-------|
| [pc #1658](https://github.com/abhimehro/personal-config/pull/1658) | `/cs-agent` already posted; MERGEABLE/UNSTABLE |
| [cs #1018](https://github.com/abhimehro/ctrld-sync/pull/1018) | CodeScene + deletes SSRF allowlist — unsafe wholesale salvage |

## AUTO-RESOLVED for Phase 1 (next cycle)

| PR | Status |
|----|--------|
| [hg #373](https://github.com/abhimehro/Hydrograph_Versus_Seatek_Sensors_Project/pull/373) | CLEAN dependabot pytest-cov |
| [hg #374](https://github.com/abhimehro/Hydrograph_Versus_Seatek_Sensors_Project/pull/374) | CLEAN dependabot numpy |
| [esp #1286](https://github.com/abhimehro/email-security-pipeline/pull/1286) | CLEAN Palette CLI styling |

## Left open (non-salvage)

| PR | Reason |
|----|--------|
| [pc #1660](https://github.com/abhimehro/personal-config/pull/1660) | MERGEABLE but tests FAIL — Phase 1 / fix cycle |
| [pc #1659](https://github.com/abhimehro/personal-config/pull/1659) | Phase 1 session docs CONFLICTING — superseded by this PR |
