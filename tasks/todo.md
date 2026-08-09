# TODO — Automated PR Salvage Phase 2 — 2026-08-09

## Plan

- [x] Preflight: `gh auth` as abhimehro, branch `cursor-agent/automated-pr-salvage-workflow-9373`, `make cursor-cloud-hooks`
- [x] Re-fetch live CONFLICTING/DIRTY/UNSTABLE bot PRs across 7 repos
- [x] Cross-check Phase 1 remainder (#1953 / Aug 9) + Aug 8 salvage memory against live state
- [x] Triage: SALVAGE / CLOSE-SUPERSEDED / ESCALATE / DEFER (never merge autonomously — S1)
- [x] Salvage recoverable DIRTY work onto fresh `main` draft PRs; close originals with cross-links
- [x] Write deliverables: `pr-inventory.md`, `pr-triage.md`, `pr-review-2026-08-09.md` Phase 2 addendum, append `salvage-session-reports.md` + lesson **0fo**
- [ ] Commit/push docs on personal-config; open/update draft docs PR via automation tools
- [ ] Update automation memory; Notion session page

## Security gates

- No autonomous merges (S1) ✅
- No force-push ✅
- Security/auth/CORS/TOCTOU/Sentinel/PBKDF2 stay ESCALATE (0fn) ✅
- Skip `request_reviewers` when author is already abhimehro (0ew) ✅
- One competing `tasks/*` docs lineage — stacked on Phase 1 #1953 tip (0fk) ✅
