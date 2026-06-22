# PR Triage — 2026-06-22

## Phase 1 duplicate & overlap groups

### Group A — repoprompt-ce Changelog DateFormatter
| PR | Files | Keeper | Action |
| --- | --- | --- | --- |
| #39 | Changelog.swift + workflow/LICENSE churn | **#39** (escalated) | ESCALATE — trust boundary |
| #27 | Changelog.swift | — | CLOSED → superseded by #39 |

### Group B — repoprompt-ce icon button a11y
| PR | Files | Keeper | Action |
| --- | --- | --- | --- |
| #25 (salvage) | focused a11y labels | **#25** | OPEN — snyk only after update-branch |
| #30 | broader duplicate | — | CLOSED → superseded by #25 |

### Group C — series_correction vectorize processor.py
| PR | Files | Keeper | Action |
| --- | --- | --- | --- |
| #142 | `processor.py` z-score vectorize | **#142** | DEFER (CodeScene) |
| #135 | outlier loop vectorize | — | CLOSED → superseded by #142 |

## Phase 2 reconciliation

| Prior tail PR | Phase 2 outcome |
| --- | --- |
| rp #28 | **CLOSED** → v3 salvage [#41](https://github.com/abhimehro/repoprompt-ce/pull/41) |
| rp #24, #25 | **OPEN** — `update-branch` cleared Style + dependency-review; snyk remains |
| rp #39 | **OPEN** — ESCALATE (deleted codacy.yml, LICENSE/README churn) |
| sc #142 | **OPEN** — DEFER; cs-agent already posted |

## Security gate review

| PR | Gate | Result |
| --- | --- | --- |
| pc #1310 | CWE-78 eval in trap | **MERGED** (Phase 1) |
| rp #41 | Keychain accessibility tighten | **T1 draft — human review** |
| rp #39 | Bot disabled Codacy/Snyk workflows | **FAIL → ESCALATE** |

## Human review queue (priority)

1. **T1:** rp [#41](https://github.com/abhimehro/repoprompt-ce/pull/41) — Keychain salvage v3
2. **T2:** rp [#39](https://github.com/abhimehro/repoprompt-ce/pull/39) — trust-boundary; cherry-pick Changelog only if wanted
3. **T3:** rp [#24](https://github.com/abhimehro/repoprompt-ce/pull/24)/[#25](https://github.com/abhimehro/repoprompt-ce/pull/25) — snyk gate; sc [#142](https://github.com/abhimehro/series_correction_project_updated/pull/142) — CodeScene tail

```yaml
open_followups:
  - repo: abhimehro/repoprompt-ce
    pr: 41
    reason: T1 Keychain salvage v3 — draft; human merge
  - repo: abhimehro/repoprompt-ce
    pr: 39
    reason: T2 ESCALATE — bot disabled security CI; scope creep
  - repo: abhimehro/repoprompt-ce
    pr: 24
    reason: T3 salvage — snyk only fail after update-branch
  - repo: abhimehro/repoprompt-ce
    pr: 25
    reason: T3 salvage — snyk only fail after update-branch
  - repo: abhimehro/series_correction_project_updated
    pr: 142
    reason: CodeScene fail; cs-agent posted
```
