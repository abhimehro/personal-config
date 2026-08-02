# PR Inventory — Salvage Session 2026-08-02

Live re-fetch after Phase 1 remainder (`tasks/pr-review-2026-08-02.md` / [#1884](https://github.com/abhimehro/personal-config/pull/1884)).
Scope: bot/automation PRs that are CONFLICTING/DIRTY (or prior deferred/escalated still open).

## Counts (live at Phase 2 start)

| Repo | Open | CONFLICTING/DIRTY | Notes |
| ---- | ---- | ----------------- | ----- |
| personal-config | 2 | 0 | #1841 CLEAN Sentinel escalate; #1884 Phase 1 docs |
| ctrld-sync | 0 | 0 | Queue drained (yesterday #1105 merged) |
| email-security-pipeline | 0 | 0 | Queue drained (#1401 merged) |
| Seatek_Analysis | 2 | 0 | #580/#573 CLEAN Sentinel escalate |
| Hydrograph… | 3 | 3 (#445/#448/#450) | All Sentinel path cluster → CLOSE-SUPERSEDED |
| series_correction… | 0 | 0 | Queue drained |
| repoprompt-ce | 13 | 7 DIRTY + 6 UNSTABLE | Salvage #171 from #165/#158; defer drift pile |

## Salvage drafts opened this run

| New draft | Salvages | Repo |
| --------- | -------- | ---- |
| [#171](https://github.com/abhimehro/repoprompt-ce/pull/171) | #165/#158 TOCTOU-only | repoprompt-ce |

## Closed this run

| PR | Disposition |
| -- | ----------- |
| hg #445 | CLOSE-SUPERSEDED — `is_safe_path` already on `main` |
| hg #448 | CLOSE-SUPERSEDED — duplicate-check corruption; fix on `main` |
| hg #450 | CLOSE-SUPERSEDED — refactor only; security on `main` |
| rpce #158 | CLOSE-SUPERSEDED by #171 |

## Still escalated / deferred (human)

- pc #1841 Sentinel timeout/auth env (CLEAN)
- seatek #580 path hijack, #573 file-read DoS (CLEAN)
- rpce #165 prefer #171; Build/Test red on original
- rpce DIRTY drift: #161/#157/#152/#148/#147/#144 (DEFER)
- rpce UNSTABLE MERGEABLE: #170/#169/#168/#164/#163 (Phase 1 REQUEST_CHANGES)
