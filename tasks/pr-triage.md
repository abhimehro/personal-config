# PR Triage — 2026-07-03

**Session:** Automated PR review & cleanup (cron 13:00 UTC)  
**Mode:** review-and-merge

## Duplicate & overlap analysis

| Group | PRs | Decision | Rationale |
|-------|-----|----------|-----------|
| ctrld UX isatty | #970 (salvage), #973 (Palette) | Merge #970 first; defer #973 | #970 is narrower salvage with all CI green; #973 extends same area but CodeScene red. #970 merged; #973 needs rebase + CodeScene remediation. |
| pc Bolt perf | #1466, #1467 | Independent | Different files (`system_metrics.sh` vs `health_check.sh`/`service_monitor.sh`). Both mergeable after #1466 autofix. |
| dependabot ruby/setup-ruby | esp #1210, sc #172 | Independent | Same bump, different repos — both merged. |

## Superseded / no-op

| Repo | PR | Action | Rationale |
|------|-----|--------|-----------|
| email-security-pipeline | #1211 | **CLOSE** | `jules_review_notes.md` only — Daily QA session artifact, no production code |

## Stale (>30 days)

None in scope.

## Disposition matrix

| Disposition | Count | PRs |
|-------------|------:|-----|
| MERGE | 12 | Seatek #397/#398; esp #1210; hg #315; sc #171/#172; pc #1467/#1458; cs #970; rpce #84/#85/#86 |
| MERGE-AFTER-FIX | 1 | pc #1466 (SC2148 shebang autofix pushed; awaiting CI) |
| DEFER | 3 | pc #1464 (Gemini review fail); cs #973 (CodeScene fail); esp #1211 → close |
| ESCALATE | 0 | — |
| CLOSE-DUPLICATE | 0 | — |
| CLOSE-NOOP | 1 | esp #1211 |

## Gate results (failures)

### personal-config #1466 — AUTO-FIX

- **Failure:** ShellCheck SC2148 on `get_repo_vars.sh` (missing shebang)
- **Fix:** Added `#!/usr/bin/env bash` header; pushed to PR branch
- **Status:** CI re-run in progress (Swift CodeQL analyze slow)

### personal-config #1464 — DEFER

- **Failure:** `review / review` (Gemini Dispatch workflow)
- **Change scope:** Security-scan workflow action version bumps (gitleaks v3, codeql v4.36.3, sbom-action, upload-artifact v7)
- **Other gates:** All security scans green
- **Decision:** Defer — failing required/advisory Gemini review on CI/INFRA workflow change; human should confirm action pin strategy

### ctrld-sync #973 — DEFER

- **Failure:** CodeScene Code Health Review
- **Remediation:** Posted `/cs-agent skill:fix-code-health-degradations` per policy
- **Decision:** Defer until CodeScene agent completes

## Security gate highlights

| PR | Gate | Notes |
|----|------|-------|
| Seatek #397 | ✅ PASS | Removes `or "gh"` path-hijack fallbacks; fail-closed on missing binaries |
| pc #1464 | ✅ PASS (scans) | Workflow-only; no secrets, no permission escalation |
| pc #1458 | ✅ PASS | Shared libs + LFS gitattributes; all security scans green |
| All merged | ✅ | No secrets, no eval/exec, no weakened `.gitignore` |

## Merge ordering applied

1. Security: Seatek #397
2. Dependencies: esp #1210, sc #172
3. CI/infra: hg #315, sc #171, rpce #84
4. Performance/UI: remaining green PRs
5. Salvage: cs #970 (after prior #965 close)
