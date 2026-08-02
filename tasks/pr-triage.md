# PR Triage — Phase 2 Salvage 2026-08-02

Decision tree applied per `docs/automated-pr-salvage-agent.md` (S1–S6).
Input: Phase 1 remainder + live CONFLICTING re-fetch. Autonomous merges: **0**.

## Disposition summary

| Disposition | Count | PRs |
| ----------- | ----: | --- |
| SALVAGE (draft) | 1 | rpce #171 ← #165/#158 |
| CLOSE-SUPERSEDED | 4 | hg #445/#448/#450; rpce #158 |
| ESCALATE (human) | 3 | pc #1841; seatek #580/#573 |
| DEFER | 6 | rpce #144/#147/#148/#152/#157/#161 |
| Phase 1 hold (UNSTABLE) | 6 | rpce #163/#164/#168/#169/#170 + note on #165 |
| Empty queues | 3 repos | ctrld / esp / series |

## Deep-dive notes

### Hydrograph #445/#448/#450

`main` already imports `is_safe_path` and guards `--output` in `validate_data.py`.
#448 contained ×7 duplicated `is_safe_path` blocks (corruption). #450 only
extracted a `ValidationReporter` refactor. No residual security gap → close.

### rpce #158 vs #165 → #171

#165 MERGEABLE but UNSTABLE: real TOCTOU fix in `MCPConfigExportService` /
`MCPTerminalRecord` mixed with `ToolOutputFormatter` `.text(text:)` churn.
Salvaged **security files only** onto draft [#171](https://github.com/abhimehro/repoprompt-ce/pull/171).
Closed CONFLICTING twin #158.

### rpce DIRTY drift pile

100–400 files vs `main` each; titled intent buried in skill/CI/vendor noise.
DEFER with re-roll guidance; prefer MERGEABLE a11y/Bolt twins after CI green.

## Security gates

- No auth/payment/schema changes implemented.
- Security salvage #171 remains **draft** for human merge (S1).
- CLEAN Sentinels left open for human (never auto-merged).
