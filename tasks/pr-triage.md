# PR Triage — 2026-06-26

## Duplicate & overlap groups

### Group A — repoprompt-ce Palette accessibility labels
| PR | Files | Keeper | Action |
| --- | --- | --- | --- |
| #60 | `AgentWorkflowsConfigureSheet.swift`, palette.md | **#60** | MERGED |
| #53 | 72 files (workflow/Trunk churn + a11y) | — | CLOSED → superseded by #60 |

### Group B — personal-config salvage session reports (tasks/*.md)
| PR | Files | Keeper | Action |
| --- | --- | --- | --- |
| #1338 | review session 2026-06-23 | **#1338** | MERGED |
| #1339 | salvage 2026-06-23 | — | CLOSED → conflicts after #1338 |
| #1346 | salvage 2026-06-24 | — | CLOSED → conflicts / superseded |
| #1355 | salvage 2026-06-25 (draft) | — | CLOSED → draft + conflicts |

## Security gate review

| PR | Gate | Result |
| --- | --- | --- |
| email-security-pipeline #1153 | Lowercase URL hostname/netloc for webhook validation | **PASS → MERGED** |
| personal-config #1356 | AppleScript `--` delimiter (CWE-74 option injection) | **PASS → MERGED** |
| repoprompt-ce #41 | Keychain `WhenUnlockedThisDeviceOnly` + test alignment | **PASS → MERGED** |
| personal-config #1352 | SHA-pinned actions → mutable tags | **FAIL → ESCALATE** |

## Infra / CI deferrals

| PR | Failing check | Action |
| --- | --- | --- |
| Hydrograph #292 | `submit-pypi` | DEFER — bump is routine; infra path unhealthy |
| repoprompt-ce #57 | `Style` (+ conflicts after merge burst) | DEFER — posted `@dependabot rebase` |

## Merge ordering applied

1. Security: esp #1153, pc #1356, rpce #41
2. Dependency: release-drafter bumps (7 repos), ctrld #950, rpce #42
3. Salvage/tests: rpce #56
4. Performance/UI: hg #299, Seatek #371, pc #1360, esp #1154, sc #155, rpce #61
5. Docs: pc #1338
6. UI keeper: rpce #60 (after closing #53)

## Post-session remainder (salvage handoff)

```yaml
- repo: personal-config
  pr: 1352
  reason: ESCALATE — workflow SHA→tag pin regression; human approval required
- repo: Hydrograph_Versus_Seatek_Sensors_Project
  pr: 292
  reason: DEFER — submit-pypi infra failure on routine actions/cache bump
- repo: repoprompt-ce
  pr: 57
  reason: DEFER — Style check + stale branch after merge burst; rebase posted
```
