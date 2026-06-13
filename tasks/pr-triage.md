# PR Triage — 2026-06-13

## Duplicate groups

| Group | Keep | Close | Rationale |
| --- | ---: | ---: | --- |
| ESP cache-clear integration test | #1102 | #1101 | 98.7% diff similarity; same file |
| ESP EmailIngestionManager refactor | #1100 | #1098 | 100% identical diff |
| personal-config session reports | #1228 (merged) | #1229 | Overlapping docs window; #1228 landed first |

## Superseded / zero-diff

| Repo | PR | Action | Rationale |
| --- | ---: | --- | --- |
| Seatek_Analysis | #306 | CLOSE | `changedFiles == 0`; lesson 0b — no effective diff vs main |
| ctrld-sync | #882 | MERGED before #890 | Smaller security fix; #890 merged separately (different diff from #886) |

## Conflict cascade (defer → Phase 2 salvage)

| Repo | PRs | Trigger |
| --- | --- | --- |
| Seatek_Analysis | #283, #282, #278, #261 | All DIRTY after security/perf merges on main |
| email-security-pipeline | #1096, #1103 | DIRTY after refactor/perf merge burst |
| ctrld-sync | #886 | DIRTY after #890 palette merge |

## Escalations

| Repo | PR | Reason |
| --- | ---: | --- |
| personal-config | #1231 | Touches `repository_automation_common.py` — PR automation toolchain trust boundary |

## Merge ordering applied

1. **Security:** series #115 (CSV injection), Seatek #307 (shell=False), ctrld #882 (placeholder leak)
2. **Dependency:** personal-config #1233 (dependabot esbuild)
3. **CI/docs:** personal-config #1228 (session report)
4. **Tests/refactors (ESP):** lint → perf micro → tests → refactors (#1094→#1100 chain)
5. **Salvage merges:** Seatek #308/#303/#302, Hydrograph #258, ESP #1088
6. **UI:** ctrld #890, repoprompt-ce #4

## Stale check

Stale threshold: 30 days. No PRs exceeded threshold (all activity within June 2026).

## CodeScene remediation posted

`/cs-agent skill:fix-code-health-degradations` posted on: #1103, #257, #114, #892, #1231.
