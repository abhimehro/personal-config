# Phase 1 PR Review — 2026-08-17

Branch: `cursor-agent/automated-pr-workflow-2dfb` Mode: review-and-merge.
Stale: 30 days. Auto-fix: safe routine only. Merge: squash.

- [x] Preflight gate (`preflight-gh-pr-automation.sh`, 7/7)
- [x] `make cursor-cloud-hooks`
- [x] Live-fetch open auto PRs (do not trust 2026-08-16 snapshot)
- [x] Classify + write `tasks/pr-inventory.md` / `tasks/pr-triage.md`
- [x] Gate 1–4 on MERGE candidates; re-check 0fs after any lock merge
- [x] Adversarial multi-model review on representative diffs
- [x] APPROVE + squash-merge green routine PRs (6)
- [x] REQUEST_CHANGES / ESCALATE security, majors, trust-boundary, failing CI
- [x] Close duplicates / zero-diff / superseded (4)
- [x] CodeScene trigger skipped (MCP down; pc#1980 already triggered 08-16)
- [x] Append `tasks/review-session-reports.md` + dated snapshot + lesson 0ft
- [x] `make test-quick` + `make lint-errors` on docs branch
- [x] Commit/push docs; open artifacts PR
- [x] Update automation memory + Notion

## Phase 2 remainder (drafts only — do not merge)

- Sentinel/CORS/TOCTOU/CWE clusters stay ESCALATE
- Majors with red CI stay ESCALATE
- 0fo/0fp/0fg/0fs/0ft HOLD until re-verified vs current main
- DIRTY ctrld#1188 uv-only → draft salvage
- Do not merge salvage drafts or auth/payment/schema PRs
