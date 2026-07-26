# PR Review Session TODO — 2026-07-25

- [x] Preflight 7/7
- [x] Inventory + triage
- [x] Merge safe PRs / autofix hg #414
- [x] Escalate security clusters + CodeScene triggers
- [x] Write pr-inventory.md, pr-triage.md, pr-review-2026-07-25.md
- [x] Update lessons.md + review-session-reports.md
- [x] Commit/push docs branch + open PR (#1771)
- [x] Update automation memory
# Phase 2 Salvage — 2026-07-25

## Phase 1
- [x] Live inventory → `tasks/pr-inventory.md`
- [x] Triage → `tasks/pr-triage.md`
- [x] Review gates (CI / security / quality)
- [x] Merge green safe PRs (squash) — 20 merged
- [x] Close duplicates / superseded / stale — 2 closed
- [x] Escalate auth/secrets/trust-boundary / tip majors — 18
- [x] Autofix esp #1346 bolt.md (Lesson 0el)
- [x] CodeScene `/cs-agent` on sc #285

## Deliverables
- [x] `pr-inventory.md`, `pr-triage.md`, `pr-review-2026-07-24.md`
- [x] Append `review-session-reports.md`; update `lessons.md` (0ej/0ek/0el)
- [x] Commit + push session docs; open session PR (#1764)
- [x] Branch `cursor-agent/automated-pr-salvage-031d`

## Live re-fetch
- [x] Import Phase 1 remainder from #1755
- [x] Classify salvage vs escalate vs close

## Salvage (draft only)
- [x] esp #1346 ← #1327 (SPF helper; close original)
- [x] esp #1347 ← #1320 (subject validate + assert; close original)
- [x] Close esp #1345 no-op

## Escalate / defer
- [x] Refresh escalate comments (pc/esp/sc/Seatek/rpce)
- [x] `/cs-agent` on esp #1346
- [x] Leave prior drafts for human

## Deliverables
- [x] pr-inventory.md, pr-triage.md, pr-review-2026-07-23.md Phase 2
- [x] salvage-session-reports.md + lessons.md (0ek–0en)
- [x] Commit + push session branch; open draft session PR


# Daily QA 2026-07-25 — personal-config

- [x] Harden `performance_optimizer.sh` against missing `bc` (Linux/CI)
- [x] Mock `bc` in `tests/test_performance_optimizer.sh`
- [x] Re-run `bash tests/test_performance_optimizer.sh` (11/11)
- [x] Preflight (`gh` via unset GH_TOKEN + hosts.yml; `make cursor-cloud-hooks`)
- [x] Re-fetch Phase 1 remainder + live inventory
- [x] Deep-dive CONFLICTING: pc #1748, #1721; sc #275; rpce #126/#127
- [x] Re-salvage pc #1748 → `cursor-agent/salvage-pc-1748-visual-recap-v2-a2fb` (MDX 9/9)
- [x] Escalate via MCP reviews; no autonomous merges
- [x] Write inventory / triage / review / salvage-session-reports / lessons (0eq)
- [x] Commit + push session branch; open docs PR #1772
- [ ] Human: open salvage draft from compare URL; close #1748 + esp #1360
