# PR Inventory — Salvage Session 2026-08-01

Live re-fetch after Phase 1 remainder (`tasks/pr-review-2026-08-01.md`).
Scope: bot/automation PRs that are CONFLICTING/DIRTY (or prior deferred/escalated still open).

## Counts (live)

| Repo | Open | CONFLICTING/DIRTY (start) | Notes |
| ---- | ---- | ------------------------- | ----- |
| personal-config | 9→ | 4 (#1859/#1857/#1825/#1822) | Salvaged 1857/1859; closed 1825; escalate 1822 |
| ctrld-sync | 3 | 1 (#1081) | Salvaged → #1105 |
| email-security-pipeline | 1 | 1 (#1399) + CodeScene | Spam-only salvage → #1401 |
| Seatek_Analysis | 6 | 4 (#568/#555/#560/#554) | #554 → #576; security escalate |
| Hydrograph… | 5 | 0 | All CLEAN (Phase 1 remainder stale on #443) |
| series_correction… | 0 | 0 | Queue drained |
| repoprompt-ce | 9 | 7 DIRTY + UNSTABLE CI | Security escalate #158; defer drift pile |

## Salvage drafts opened this run

| New draft | Salvages | Repo |
| --------- | -------- | ---- |
| [#1875](https://github.com/abhimehro/personal-config/pull/1875) | #1857 | personal-config |
| [#1876](https://github.com/abhimehro/personal-config/pull/1876) | #1859 (empty-state only) | personal-config |
| [#1105](https://github.com/abhimehro/ctrld-sync/pull/1105) | #1081 | ctrld-sync |
| [#1401](https://github.com/abhimehro/email-security-pipeline/pull/1401) | #1399 (spam_analyzer only) | email-security-pipeline |
| [#576](https://github.com/abhimehro/Seatek_Analysis/pull/576) | #554 | Seatek_Analysis |

## Closed this run

| PR | Disposition |
| -- | ----------- |
| pc #1857 | superseded by #1875 |
| pc #1859 | superseded by #1876 |
| pc #1825 | no-op junk |
| ctrld #1081 | superseded by #1105 |
| esp #1399 | superseded by #1401 |
| seatek #554 | superseded by #576 |

## Still escalated / deferred (human)

- pc #1822 CORS (DIRTY Sentinel)
- seatek #568 path hijack, #555 multi-root, #560 parallelize (REQUEST_CHANGES)
- seatek #571/#573 CLEAN security awaiting human
- hg #445/#448/#450/#441 CLEAN security/deps
- rpce #158 TOCTOU + DIRTY drift cluster (#161/#157/#152/#148/#147/#144)
- rpce #163/#164 UNSTABLE CI (MERGEABLE — Phase 1 territory)
- ctrld #1086 CLEAN but prior REQUEST_CHANGES (pin scope)
- pc #1841 CLEAN Sentinel; #1867 UNSTABLE Bolt
