# PR Triage — 2026-06-21

## Duplicate & overlap groups

### Group A — personal-config infuse-media-server a11y
| PR | Files | Keeper | Action |
| --- | --- | --- | --- |
| #1303 | `infuse-media-server.py`, tests, palette.md | **#1303** | MERGED |
| #1301 | same core files | — | CLOSED → superseded by #1303 |

### Group B — ctrld-sync restart prompt EOF handling
| PR | Files | Keeper | Action |
| --- | --- | --- | --- |
| #930 | `main.py` only | **#930** | MERGED |
| #928 | `main.py`, bolt.md | — | CLOSED → duplicate of #930 |

### Group C — series_correction vectorize processor.py
| PR | Files | Keeper | Action |
| --- | --- | --- | --- |
| #135 | `processor.py` (outlier loop) | **#135** | DEFER (CodeScene) |
| #121 | `processor.py` (z-score/jump) | — | CLOSED → superseded by #135 |

### Group D — repoprompt-ce Changelog DateFormatter
| PR | Files | Keeper | Action |
| --- | --- | --- | --- |
| #27 | Changelog.swift + workflow | **#27** | DEFER (Style) |
| #22 | Changelog.swift, bolt.md | — | CLOSED → superseded by #27 |

### Group E — repoprompt-ce icon button a11y
| PR | Files | Keeper | Action |
| --- | --- | --- | --- |
| #25 (salvage) | focused salvage | **#25** | DEFER (Style) |
| #26 (Palette) | broader Palette churn | — | CLOSED → superseded by #25 |

## Superseded / zero-diff

| PR | Reason |
| --- | --- |
| Seatek #342 | Zero-diff daily QA PR (0 bytes changed) |
| personal-config #1300 | Draft session-report PR; canonical reports live on agent branch |

## Security gate review

| PR | Gate | Result |
| --- | --- | --- |
| Seatek #343 | Null-byte check before `realpath` | **PASS → MERGED** |
| personal-config #1287 | AppleScript `--` separator (CWE-74) | **PASS → MERGED** |
| personal-config #1304 | Workflow YAML corruption + tag pinning | **FAIL → ESCALATE** |
| repoprompt-ce #23 | Keychain accessibility tighten | **PASS logic; CI fail → DEFER salvage** |

## CodeScene remediation

Posted `/cs-agent skill:fix-code-health-degradations` on:
- series_correction #121 (before close)
- series_correction #134
- series_correction #135

## Merge ordering applied

1. Security: Seatek #343, personal-config #1287
2. Routine CLEAN: esp #1136, pc #1307, pc #1303, pc #1288, ctrld #930, sc #134
3. Auto-fix: pc #1308 (bolt.md conflict after #1307 merge)
4. Closes: duplicates and zero-diff after keeper merged

## Deferred tail → Salvage Agent

```yaml
open_followups:
  - repo: abhimehro/personal-config
    pr: 1304
    reason: ESCALATE — corrupted workflow YAML + action pin regression
  - repo: abhimehro/series_correction_project_updated
    pr: 135
    reason: CodeScene fail after cs-agent; perf vectorize
  - repo: abhimehro/repoprompt-ce
    pr: 23
    reason: T1 security salvage — Keychain; Style+Build fail
  - repo: abhimehro/repoprompt-ce
    pr: 24
    reason: T3 salvage — Linux release tests; Style fail
  - repo: abhimehro/repoprompt-ce
    pr: 25
    reason: T3 salvage — a11y labels; Style fail
  - repo: abhimehro/repoprompt-ce
    pr: 27
    reason: Bolt perf — Style + dependency-review fail
```

---

## Phase 2 salvage triage — 2026-06-21 evening

### Reconciliation

| Prior tail PR | Phase 2 outcome |
| --- | --- |
| pc #1304 | **CLOSED** → infra-fix [#1311](https://github.com/abhimehro/personal-config/pull/1311) |
| sc #135 | **OPEN** — CodeScene still failing; cs-agent already posted |
| rp #23 | **CLOSED** → v2 salvage [#28](https://github.com/abhimehro/repoprompt-ce/pull/28) |
| rp #24, #25, #27 | **OPEN** — blocked by mashed `dependency-review.yml` on `main`; infra-fix [#29](https://github.com/abhimehro/repoprompt-ce/pull/29) |

### New arrivals (post–Phase 1)

| PR | Disposition |
| --- | --- |
| pc [#1310](https://github.com/abhimehro/personal-config/pull/1310) | T1 human review — CWE-78; CI green |
| ctrld [#932](https://github.com/abhimehro/ctrld-sync/pull/932) | DEFER — CodeScene; cs-agent posted this session |
| esp [#1138](https://github.com/abhimehro/email-security-pipeline/pull/1138) | Phase 1 merge candidate — CLEAN |

### Human review queue (priority)

1. **T0:** pc [#1311](https://github.com/abhimehro/personal-config/pull/1311), rp [#29](https://github.com/abhimehro/repoprompt-ce/pull/29)
2. **T1:** pc [#1310](https://github.com/abhimehro/personal-config/pull/1310), rp [#28](https://github.com/abhimehro/repoprompt-ce/pull/28)
3. **T3:** esp [#1138](https://github.com/abhimehro/email-security-pipeline/pull/1138), ctrld [#932](https://github.com/abhimehro/ctrld-sync/pull/932), sc [#135](https://github.com/abhimehro/series_correction_project_updated/pull/135), rp [#24](https://github.com/abhimehro/repoprompt-ce/pull/24)/[#25](https://github.com/abhimehro/repoprompt-ce/pull/25)/[#27](https://github.com/abhimehro/repoprompt-ce/pull/27)
