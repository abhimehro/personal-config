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

# PR Review Session 2026-07-21 — todo

- [x] Preflight gate — PASS 7/7
- [x] Inventory → `tasks/pr-inventory.md`
- [x] Triage → `tasks/pr-triage.md`
- [x] Gate 1–4 review + act (60 merge / 13 close / 10 escalate / 13 defer)
- [x] Write `tasks/pr-review-2026-07-21.md` + append `review-session-reports.md`
- [x] Update `tasks/lessons.md` (0ef, 0eg)
- [x] Commit + push docs on `cursor-agent/pr-workflow-automation-8b69`
- [x] Open docs PR https://github.com/abhimehro/personal-config/pull/1732
