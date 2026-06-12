# PR Triage — 2026-06-12

**Mode:** review-and-merge (Phase 1)  
**Preflight:** PASS  
**Input:** Live GitHub state + prior deferred tail from `tasks/pr-review-2026-06-11.md`

## Triage matrix

| Disposition | Count | Action |
| --- | ---: | --- |
| MERGE | 14 | Squash-merged with branch delete |
| CLOSE-DUPLICATE | 1 | #1226 superseded by #1227 |
| CLOSE-SUPERSEDED | 1 | #1216 superseded by merged #1219 |
| DEFER | 9 | Salvage / infra / CodeScene / benchmark |
| ESCALATE | 0 | — |

## Duplicate & overlap analysis

| Group | Keeper | Action on others | Rationale |
| --- | --- | --- | --- |
| Bolt category hoist (personal-config) | **#1227** | Close #1226 | Same `_CATEGORIES` tuple refactor; #1227 omits `.jules/bolt.md` churn |
| Session doc drafts (personal-config) | **#1219** (merged) | Close #1216 | Conflicting cursor-agent draft superseded by merged salvage report |
| ESP alert perf | **#1081** | — | No file overlap with #1084 or #1082 |
| Seatek `Updated_Seatek_Analysis.R` | **#296** then **#297** | Merge #296 first | Both touched analysis script; sequential merge succeeded |

No other semantic duplicates detected.

## Per-PR notes

### personal-config #1210 — MERGE

Jules test: `FileNotFoundError` path in `parse_inventory._load_inventory_lines`. All gates green.

### personal-config #1227 — MERGE (keeper)

Bolt perf: hoist `_CATEGORIES` tuple in `categorize_ready.py`. Closed duplicate #1226.

### personal-config #1225 — MERGE

Daily QA: six test-file lint/format fixes only. No production code.

### personal-config #1221 — MERGE

Palette: `aria-hidden` on decorative emoji in media-server listings. Accessibility-only.

### personal-config #1216 — CLOSE-SUPERSEDED

Conflicting session-doc PR; #1219 already merged 2026-06-12.

### ctrld-sync #882 — DEFER

Palette UX fix only (+5/-1). Benchmark check still failing (shared infra issue from #881 era). Security gates green.

### email-security-pipeline #1081/#1084/#1082 — MERGE

- #1081: parallel external alert dispatch (salvages #1071)
- #1084: remove `re.IGNORECASE` penalty; case-fold at search time
- #1082: de-emphasize secondary terminal hints

Merged in order: perf salvage → regex perf → Palette UI (no file overlap).

### email-security-pipeline #1075 — DEFER

Conflicting Jules test PR for setup wizard. Route to Phase 2 salvage.

### Seatek_Analysis #296/#297/#286/#284/#277 — MERGE

Routine test additions and Bolt perf on disjoint or sequentially mergeable files. #296 merged before #297 (shared `Updated_Seatek_Analysis.R`).

### Seatek_Analysis #283/#261/#282/#278/#276/#291 — DEFER

- #283: T1 security (`shell=False`) — 15-file DIRTY PR; needs intent-file salvage v2
- #261: prior perf salvage; Gate 2 risk (Lesson 0ci)
- Remaining: conflict batch from main movement

### series_correction #114 — DEFER

CodeScene code health failing. Posted `/cs-agent skill:fix-code-health-degradations` before defer.

### repoprompt-ce #2/#3 — MERGE

Bolt DateFormatter reuse + Palette copy-button `aria-label`s. Bugbot-only CI (no macOS build gate in repo).

## Security gate review

- **Gate 2 pass:** All merged PRs — no secrets, no auth changes, no subprocess weakening
- **Gate 2 block (deferred):** #283 (security intent, needs human-reviewed salvage), #261 (control removal risk)
- **Substantive CI block:** #882 benchmark, #114 CodeScene
