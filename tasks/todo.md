# Phase 2 Salvage — 2026-08-12

## Preflight
- [x] `gh auth status` (abhimehro PAT active)
- [x] `make cursor-cloud-hooks`
- [x] Read salvage policy + automation memory
- [x] Live-fetch CONFLICTING bot/automation PRs
- [x] Load Phase 1 remainder from #1977

## CONFLICTING queue
- [x] pc #1977 — recover into Phase 2 docs PR (0fk); closed via #1979
- [x] ctrld #1150 → draft #1159; closed
- [x] Hydro #504 → draft #507; closed
- [x] series #378 → CLOSE no-op
- [x] rpce #231 → HOLD/ESCALATE comment
- [x] rpce #224 → draft #237; closed

## Deliverables
- [x] `tasks/pr-inventory.md`, `pr-triage.md`, `pr-review-2026-08-12.md`
- [x] Append `tasks/salvage-session-reports.md` + Lesson 0fq
- [x] Open draft docs PR #1979; close #1977; Notion + memory
# Phase 1 PR Review — 2026-08-16

Branch: `cursor-agent/automated-pr-workflow-9b3f`
Mode: review-and-merge. Preflight: PASS 7/7.

- [x] Preflight gate
- [x] Inventory open auto PRs (68 auto + 2 human OOS)
- [x] Classify + write `tasks/pr-inventory.md` / `tasks/pr-triage.md`
- [x] Gate 1–4 review on MERGE candidates (deps, SHA pins, palette, bolt, zero-diff)
- [x] Adversarial multi-model review on representative diffs
- [x] APPROVE + squash-merge green routine PRs (9)
- [x] REQUEST_CHANGES / ESCALATE security, majors, trust-boundary, failing CI
- [x] Close duplicates / zero-diff / superseded (2)
- [x] CodeScene trigger on failing code-health PRs (#1183, #1980)
- [x] Append `tasks/review-session-reports.md` + dated snapshot + lesson 0fs
- [x] `make test-quick` + `make lint-errors` on docs branch
- [x] Commit/push docs; open artifacts PR
- [x] Update automation memory

## Phase 2 remainder (drafts only — do not merge)

- Sentinel/CORS/TOCTOU/CWE clusters (pc #1907/#2007/#2000/#1989/#1980; hg #524/#520/#507; seatek DoS/yaml; rpce #254/#250/#243/#239; ctrld #1156)
- Majors with red CI (seatek #661, series #393/#386, esp #1444, ctrld #1136)
- 0fo/0fp/0fg HOLD (ctrld #1161, series #390, hg #523, rpce #247)
- Stale repo-health pin ctrld #1162 (0fs) — re-pin or close
- Do not merge esp #1473 (requirements-ci as default install)
- DIRTY salvage docs pc #1988/#1979 — leave
