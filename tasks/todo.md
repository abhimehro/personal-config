# Clear PR #1733 CI gates (Gitleaks + CodeScene) — 2026-07-21

**Route:** T3+S
**Context:** Visual-recap MDX harden verified live; remaining red checks block merge.

## Plan
- [x] Gitleaks: FP `secret contained` in Lesson 0ei (commit range scan) → stopword + rephrase
- [x] CodeScene: refactor `scripts/fix-recap-mdx-diff-strings.js` complexity; post `/cs-agent`
- [x] Re-run tests; commit; push; confirm checks

---

# Fix PR Visual Recap CLI failures (2026-07-21)

**Route:** T3+S
**Symptom:** Non-skip runs fail at Collect bounded diff with `spawn tsx ENOENT`.

## Root cause
- `@agent-native/core` bin falls back to `spawn("tsx")` when npm extract makes src newer than dist.
- #1715 installed `tsx` but did not put `node_modules/.bin` on PATH → still ENOENT.
- Correct consumer package: `@agent-native/recap-cli` (built dist, no tsx).

## Plan
- [x] Switch install to `@agent-native/recap-cli`
- [x] Verify locally; update docs/lesson; commit + PR

---

# Fix PLAN_RECAP_TOKEN newline / JWT leak in sticky comment (2026-07-21)

**Route:** T3+S
**Symptom:** Sticky comment `Visual recap — generation failed` with
`Headers.append: "Bearer [redacted] <jwt-remainder>" is an invalid header value`.

- [x] Sanitize token at job start (strip all whitespace / Bearer prefix)
- [x] Scrub diagnostics before sticky comment / check complete
- [x] Lesson 0ei + operator docs; warn to rotate exposed token
- [x] Commit, push, re-run visual-recap on PR (auth fixed; residual 422 = bad MDX from agent)

---

# Harden Plan MDX Diff strings / acorn 422 (2026-07-21)

**Route:** T3+S
**Symptom:** After auth fix, publish returns
`422 … plan.mdx:N:M: Could not parse expression with acorn`
(Diff `after:` embeds shell `[^[:space:]\"]` which ends the JS string early).

## Plan
- [x] Deterministic Diff `before`/`after`/`code` string fixer in sanitize (before publish)
- [x] One-shot OpenCode (+ claude/codex) repair loop when `repairable=true`
- [x] Lesson 0ej + operator docs note
- [x] Unit test for fixer; verify against failing artifact
- [x] Commit, push, update PR #1733

---

# Harden Plan MDX bare array attrs (2026-07-21)

**Route:** T3+S
**Symptom:** After JSX string-attr rewrite, publish still 422s with
`Unexpected character \`[\` before attribute value` (`columns=[…]` / `rows=[…]`)
plus illegal commas between JSX attrs.

## Plan
- [x] `fixBareArrayAttrs` + `fixJsxAttrTrailingCommas` in deterministic fixer
- [x] Workflow sanitize diagnostics include `arrayAttr` / `attrComma` counts
- [x] Unit tests + verify against `/tmp/vr-art2` artifact (`MDX_OK`)
- [x] Lesson 0ej follow-on + operator docs; commit, push, re-label visual-recap

---

# PR Review Session 2026-07-21 — todo
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
