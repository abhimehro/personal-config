# PR Triage — 2026-06-18

**Mode:** salvage-and-cleanup (Phase 1 + Phase 2)  
**Preflight:** PASS (6/6)  
**Input:** Live GitHub state + deferred tail from 2026-06-17 session

## Triage matrix

| Disposition | Count | Action |
| --- | ---: | --- |
| MERGE (Phase 1) | 1 | pc #1278 |
| SALVAGE (rebuild draft PR) | 1 | ctrld #908 → #915 |
| CLOSE-SUPERSEDED | 1 | ctrld #908 |
| AUTO-RESOLVED (prior tail) | 3 | pc #1270, esp #1120, hg #269 |
| DEFER T1 security | 2 | pc #1279, hg #272 |
| ESCALATE T2 trust boundary | 1 | pc #1275 |
| DEFER CodeScene tail | 1 | sc #121 |
| ESCALATE T0 | 0 | — |

## Infra detection

**No whole-repo infra breakage detected.** All configured repos have readable `main` CI baselines.

## Classification

| Repo | PR | Category | Gates | Decision |
| --- | ---: | --- | --- | --- |
| personal-config | 1278 | PERFORMANCE | CI green, security pass | MERGE |
| personal-config | 1279 | SECURITY | Sentinel CWE-74; Swift CodeQL in progress | DEFER T1 |
| personal-config | 1275 | CI/INFRA | Workflow pin; trust boundary | ESCALATE T2 |
| ctrld-sync | 908 | REFACTOR | DIRTY after main advance | SALVAGE → #915 |
| ctrld-sync | 915 | REFACTOR | Rebuilt; pytest 341 passed | DEFER draft review |
| Hydrograph | 272 | SECURITY | Path traversal defense; CI green | DEFER T1 |
| series_correction | 121 | PERFORMANCE | CodeScene fail; cs-agent exhausted | DEFER |

## Duplicate / supersede analysis

- **pc #1270** closed superseded by merged #1273 (same Palette WCAG intent).
- **ctrld #908** superseded by rebuilt #915 from current `main` (Lesson 0cp).
- No duplicate clusters among open PRs at EOD.

## Merge ordering applied

1. Security-classified PRs deferred for human review (no autonomous merge).
2. Performance #1278 merged (CLEAN, all checks green).
3. Salvage rebuild for DIRTY ctrld tail before closing original.
