# PR Inventory — 2026-07-18 (Phase 2 salvage) — FINAL

Preflight: **PASS** (7/7 repos). Mode: Phase 2 salvage (draft-only). Stale: 30d. **Autonomous merges: 0**.

## Live re-fetch (start of Phase 2, ~17:05 UTC)

| Repo | PR | Author | Title | CI | Conflicts | Disposition |
|------|-----|--------|-------|----|-----------|-------------|
| personal-config | [#1685](https://github.com/abhimehro/personal-config/pull/1685) | cursor | Phase 1 session docs | — | CLEAN draft | **FOLD→this PR** |
| personal-config | [#1670](https://github.com/abhimehro/personal-config/pull/1670) | cursor-agent | workflow consolidation (ABHI-1321) | prior green | **CONFLICTING** | **ESCALATE** (no salvage) |
| ctrld-sync | — | — | no open PRs | — | — | clear |
| email-security-pipeline | — | — | no open PRs | — | — | clear |
| Seatek_Analysis | — | — | no open PRs | — | — | clear |
| Hydrograph… | [#374](https://github.com/abhimehro/Hydrograph_Versus_Seatek_Sensors_Project/pull/374) | dependabot | numpy 1.26→2.2 | green | MERGEABLE | **ESCALATE** |
| series_correction… | [#233](https://github.com/abhimehro/series_correction_project_updated/pull/233) | Jules | user auth logic | green | MERGEABLE | **ESCALATE** |
| repoprompt-ce | [#126](https://github.com/abhimehro/repoprompt-ce/pull/126) | dependabot | download-artifact major | green | MERGEABLE | **ESCALATE** |
| repoprompt-ce | [#127](https://github.com/abhimehro/repoprompt-ce/pull/127) | dependabot | upload-artifact major | green | MERGEABLE | **ESCALATE** |

## Phase 1 carry-forward (already resolved this morning)

| PR | Outcome |
|----|---------|
| pc #1677/#1678/#1679 | Merged (prior salvage drafts) |
| esp #1267 | Merged (GG cleared) |
| hg #381 | Closed superseded (#378) |

## End-of-Phase-2 open remainder

| Repo | Open | Notes |
|------|------|-------|
| personal-config | 1 (#1670 DIRTY) | human: resolve shellcheck keep-vs-delete + Gemini/gitleaks review |
| ctrld-sync | 0 | clear |
| email-security-pipeline | 0 | clear |
| Seatek_Analysis | 0 | clear |
| Hydrograph… | 1 (#374) | numpy major |
| series_correction… | 1 (#233) | auth |
| repoprompt-ce | 2 (#126/#127) | tip-release artifact majors |

**Totals:** 6 open investigated → 0 salvaged, 0 closed (except folding #1685), 5 escalations carried, 0 autonomous merges.
