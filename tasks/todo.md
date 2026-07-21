# Fix PR Visual Recap CLI failures (2026-07-21)

**Route:** T3+S
**Symptom:** Non-skip runs fail at Collect bounded diff with `spawn tsx ENOENT`.

## Root cause
- `@agent-native/core` bin falls back to `spawn(\"tsx\")` when npm extract makes src newer than dist.
- #1715 installed `tsx` but did not put `node_modules/.bin` on PATH → still ENOENT.
- Correct consumer package: `@agent-native/recap-cli` (built dist, no tsx).

## Plan
- [x] Switch install to `@agent-native/recap-cli`
- [x] Verify locally; update docs/lesson; commit + PR

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
