# PR Triage — 2026-05-22

**Session:** Automated PR salvage (Phase 2, cron `0 17 * * *`).  
**Preflight:** PASS — all six configured repos.

## SALVAGED (draft v2 PR opened; originals closed)

| Repo | Old PR | New PR | Disposition |
| --- | ---: | ---: | --- |
| personal-config | 992 | 1020 | Tests-only rebuild (`tests/test_scratch_triage.py`) |
| personal-config | 995 | 1021 | AdGuard parallel IO only (no toolchain files) |
| email-security-pipeline | 867 | 894 | `alert_system.py` only; corrupt `.jules/palette.md` tail omitted |
| Seatek_Analysis | 188 | 204 | `code_health_scanner.py` cherry-pick onto `main` |

## ESCALATE (human review; no auto-merge)

| Repo | PR | Reason |
| --- | ---: | --- |
| personal-config | 985 | T2 trust boundary — `parse_inventory.py` + GH token env fail-closed rewrite; DIRTY; overlaps merged #1005 theme |

## DEFER — CONFLICTING (next salvage wave)

| Repo | PRs | Reason |
| --- | --- | --- |
| Seatek_Analysis | 190–198 (8) | batch1 salvage branches DIRTY after #189/#202 merges |
| email-security-pipeline | 807, 823, 841 | conflicts on hot paths |

## DEFER — UNSTABLE CI

| Repo | PR | Blocker |
| --- | ---: | --- |
| ctrld-sync | 789 | mypy |
| ctrld-sync | 815, 821 | CodeScene |
| ctrld-sync | 818 | greeting |
| email-security-pipeline | 842, 844 | CodeScene |
| Seatek_Analysis | 172 | CodeScene |
| series_correction | 55, 58 | CodeScene (review #58 first; close #55 if duplicate) |

## NEW DRAFT SALVAGE (awaiting CI + human merge)

| Repo | PR | Tier |
| --- | ---: | --- |
| personal-config | 1020, 1021 | T3 |
| email-security-pipeline | 894 | T1 |
| Seatek_Analysis | 204 | T3 |

## BLOCKED / NONE

| Repo | Action |
| --- | --- |
| Hydrograph_Versus_Seatek_Sensors_Project | No open PRs — preflight now PASS (was blocked 2026-05-21) |

## CLOSE-STALE / CLOSE-DUPLICATE

None closed as stale this session. Sentinel #55 vs #58 flagged for human duplicate resolution.
