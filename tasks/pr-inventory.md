# PR Inventory — 2026-07-22 (Phase 2 Salvage)

**Preflight:** PASS 7/7 (+ `make cursor-cloud-hooks`)  
**Mode:** salvage (draft-only; never auto-merge)  
**Agent branch:** `cursor-agent/automated-pr-salvage-6463`  
**Input:** Phase 1 remainder from `tasks/pr-review-2026-07-22.md` (17 PRs)  
**Live re-fetch:** 17 → dispositions below

| Repo | Open (live) | Notes |
|------|------------:|-------|
| personal-config | 4+1 draft | #1744/#1721 escalate; #1747 Phase1 docs DIRTY; new salvage [#1748](https://github.com/abhimehro/personal-config/pull/1748) |
| ctrld-sync | 0 | — |
| email-security-pipeline | 7+2 drafts | escalations + CodeScene defer; new [#1341](https://github.com/abhimehro/email-security-pipeline/pull/1341)/[#1342](https://github.com/abhimehro/email-security-pipeline/pull/1342) |
| Seatek_Analysis | 2 | #507/#511 escalate |
| Hydrograph… | 0 | — |
| series_correction… | 3 | auth cluster escalate |
| repoprompt-ce | 2 | tip artifact majors (0dw) |

## Phase 1 remainder disposition (live)

| Prior | Live state | Phase 2 action |
|-------|------------|----------------|
| pc #1733 | DIRTY | SALVAGE → draft [#1748](https://github.com/abhimehro/personal-config/pull/1748); closed #1733 |
| pc #1744 | DIRTY | ESCALATE (Actions SHA→tag unpin) |
| pc #1721 | DIRTY | ESCALATE (GH_TOKEN/env cache + workflow noise) |
| esp #1335 | DIRTY | RE-SALVAGE → draft [#1341](https://github.com/abhimehro/email-security-pipeline/pull/1341); closed #1335 |
| esp #1330 | DIRTY | SALVAGE adapted → draft [#1342](https://github.com/abhimehro/email-security-pipeline/pull/1342); closed #1330 |
| esp #1327 | DIRTY + CodeScene fail | DEFER (`/cs-agent` already posted) |
| esp #1320 | CLEAN + request-changes | DEFER (weakened test) |
| esp #1328/#1324/#1319 | CLEAN | ESCALATE (secrets/auth/token CLI) |
| sc #275/#276/#268 | OPEN (#275 DIRTY) | ESCALATE (0ef dummy_todos auth) |
| Seatek #507/#511 | CLEAN / UNSTABLE | ESCALATE (subprocess env / security refactor) |
| rpce #126/#127 | CLEAN | ESCALATE (0dw tip artifacts) |
| pc #1747 | DIRTY draft | Session docs absorbed here; leave Phase1 PR for human close after this lands |

## Conflicted bot / automation PRs (scope filter)

Authors/branches matching dependabot, renovate, Jules, Devin, Copilot, cursor-agent, Bolt/Sentinel automation patterns — conflicted subset only targeted for salvage when value remained off `main`.
