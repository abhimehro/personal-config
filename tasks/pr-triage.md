# PR Triage — 2026-06-29

## Duplicate & overlap analysis

| Group | PRs | Decision | Rationale |
|-------|-----|----------|-----------|
| rpce a11y labels | #72, #73 | Close #73; merge #72 | Same `AgentMessageBubble` labels; #72 adds `AgentRuntimeExportCard` labels and explicitly omits Apache→MIT LICENSE from escalated #70 |
| esp daily QA | #1167 | Close | Zero file diff; health report only |
| pc session reports | #1369, #1370, #1375, #1376 | Defer | Draft `app/cursor` session-report PRs; not throughput targets |

No other >90% file-overlap duplicates detected.

## Security gate notes

| PR | Gate | Result |
|----|------|--------|
| pc #1379 | CI/INFRA least-privilege | **FAIL** — SHA pins replaced with mutable `@v*` tags across 7 workflows |
| pc #1381 | Trust boundary (DNS/VPN) | **ESCALATE** — `ctrld` bind `0.0.0.0` in combined Windscribe mode; human review required |
| esp #1166 | Threat-detection logic | **PASS** — `MASTER_SPAM_PATTERN` uses pre-lowercased keywords; matching already uses `subject_lower` |
| rpce #72 | License boundary | **PASS** — salvage excludes LICENSE/README changes from #70 |
| sc #161 | Dependency review | **PASS** — `actions/cache` 6.0.0 → 6.1.0 only |

## CodeScene

| PR | CodeScene | Action |
|----|-----------|--------|
| pc #1381 | FAILURE | Posted `/cs-agent skill:fix-code-health-degradations`; merge blocked |
| All others reviewed | SUCCESS or N/A | Proceeded |

## Disposition summary

| Disposition | Count | PRs |
|-------------|-------|-----|
| MERGE | 7 | ctrld #956; esp #1164, #1166; hg #304; sc #161; rpce #72, #74 |
| CLOSE | 2 | esp #1167 (zero-diff); rpce #73 (superseded) |
| ESCALATE | 2 | pc #1379 (SHA→tag); pc #1381 (CodeScene + network) |
| DEFER | 4 | pc #1369, #1370, #1375, #1376 (draft reports) |

## End-of-day open queue

| Repo | Open in-scope |
|------|----------------|
| personal-config | 6 (#1379, #1381 + 4 draft reports) |
| ctrld-sync | 0 |
| email-security-pipeline | 0 |
| Seatek_Analysis | 0 |
| Hydrograph_Versus_Seatek_Sensors_Project | 0 |
| series_correction_project_updated | 0 |
| repoprompt-ce | 0 |
