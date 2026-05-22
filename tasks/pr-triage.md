# PR Triage — 2026-05-21

**Session:** Automated PR review-and-merge (cron `0 13 * * *`).  
**Preflight:** Partial — Hydrograph repo inaccessible; five repos processed.

## MERGED (squash, branch deleted)

| Repo | PR | Notes |
| --- | ---: | --- |
| personal-config | 1010 | Zero-diff Jules Daily QA — all required checks green enough to merge |
| ctrld-sync | 833 | Zero-diff Jules Daily QA |

## ESCALATE (human review required)

| Repo | PR | Reason |
| --- | ---: | --- |
| personal-config | 1009 | Trust boundary: modifies `parse_inventory.py` (agent toolchain); CI CLEAN |
| Seatek_Analysis | 202 | Trust boundary: `.github/scripts/repository_automation_tasks.py`; overlaps #199 hotspot; CI CLEAN |

Review comments posted on both PRs.

## DEFER — CONFLICTING (salvage / v2 rebuild from `main`)

| Repo | PRs | Reason |
| --- | --- | --- |
| personal-config | 985, 992, 995 | batch2 salvages DIRTY on `main` |
| email-security-pipeline | 807, 823, 841, 867 | conflicts after prior merges |
| Seatek_Analysis | 188–198 (9 PRs) | salvage batch1 DIRTY after #199/#175/#200 wave |

## DEFER — UNSTABLE CI (do not merge)

| Repo | PR | Blocker |
| --- | ---: | --- |
| ctrld-sync | 789 | `mypy` |
| ctrld-sync | 815, 821 | CodeScene |
| ctrld-sync | 818 | `greeting` |
| email-security-pipeline | 842, 844 | CodeScene |
| Seatek_Analysis | 172 | CodeScene |
| Seatek_Analysis | 189 | CodeScene pending |

## BLOCKED — REPO ACCESS

| Repo | Action |
| --- | --- |
| Hydrograph_Versus_Seatek_Sensors_Project | Escalate GitHub App installation / token scope; no inventory or writes |

## CLOSE-STALE / CLOSE-DUPLICATE

None this session (no PRs >30 days; duplicates left for salvage pass to avoid mistaken closure).

## READY (CLEAN, not merged)

| Repo | PR | Why held |
| --- | ---: | --- |
| personal-config | 1009 | ESCALATE toolchain |
| Seatek_Analysis | 202 | ESCALATE toolchain |
