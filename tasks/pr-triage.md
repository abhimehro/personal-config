# PR Triage — 2026-06-25

## Conflict queue (DIRTY at start)

| PR | Root cause | Salvage strategy |
| --- | --- | --- |
| esp#1152 | `app_runner.py` UI lines diverged on `main` since Jules QA opened | Fresh branch; apply URL `.lower()` + adapted UI lines only |
| rp#50 | Workflow drift + stale `test-suite-contract-ledger.tsv` deletions | Source/test scripts only; omit workflows and ledger |
| rp#44 | `codacy.yml` deleted on `main`; dependabot branch still references it | **CLOSE-STALE** — no salvage value |

## Duplicate & overlap groups

### Group A — repoprompt-ce dependabot checkout bumps
| PR | Files | Keeper | Action |
| --- | --- | --- | --- |
| #44 | 9 workflow files (checkout 4→7) | — | **CLOSED** — stale; `main` already @v6 + SHA pins |
| #42 | cache bump | **#42** | DEFER (Style fail; not conflicted) |

### Group B — repoprompt-ce cross-platform tooling
| PR | Files | Keeper | Action |
| --- | --- | --- | --- |
| #56 (salvage) | Scripts/*.py, Package.swift | **#56** | DRAFT — human review |
| #50 | above + workflows + ledger regressions | — | CLOSED → superseded by #56 |

### Group C — email-security-pipeline Jules Daily QA
| PR | Files | Keeper | Action |
| --- | --- | --- | --- |
| #1153 (salvage) | 5 src files (URL + UI) | **#1153** | DRAFT T1 security review |
| #1152 | same intent, conflicted | — | CLOSED → superseded by #1153 |

## Superseded / stale

| PR | Reason |
| --- | --- |
| esp#1152 | Superseded by salvage #1153 |
| rp#50 | Superseded by salvage #56 (ledger deletions excluded) |
| rp#44 | Stale dependabot branch; `codacy.yml` removed from `main` |

## Security gate review

| PR | Gate | Result |
| --- | --- | --- |
| esp#1153 | URL netloc/hostname `.lower()` (SSRF bypass) | **PASS logic → DRAFT T1** |
| rp#41 | Keychain accessibility tighten | **PASS logic; Style fail → DEFER T1 human** |
| rp#53 | Palette a11y labels | **PASS logic; Style fail → DEFER** |

## Infra detection

| Repo | Signal | Verdict |
| --- | --- | --- |
| Hydrograph | `submit-pypi` fail on #292 only; **green on `main`** | Not infra-broken — PR-specific defer |
| repoprompt-ce | Style fail cluster on #41/#42/#53 | Shared gate; not conflict-driven |
| email-security-pipeline | All checks green on #1152 despite DIRTY | Conflict-only; salvage unblocked |

## Deferred remainder (next session)

```yaml
open_followups:
  - repo: abhimehro/email-security-pipeline
    pr: 1153
    reason: T1 salvage draft — human security review + merge
  - repo: abhimehro/repoprompt-ce
    pr: 56
    reason: T3 salvage draft — human review + merge
  - repo: abhimehro/repoprompt-ce
    pr: 41
    reason: T1 Keychain v3 — Style fail; human security review
  - repo: abhimehro/repoprompt-ce
    pr: 53
    reason: T3 Palette a11y — Style fail
  - repo: abhimehro/repoprompt-ce
    pr: 42
    reason: T3 dependabot cache — Style fail
  - repo: abhimehro/Hydrograph_Versus_Seatek_Sensors_Project
    pr: 292
    reason: T3 dependabot cache — submit-pypi fail on PR branch
```
