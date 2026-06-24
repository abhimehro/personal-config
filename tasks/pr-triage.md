# PR Triage — 2026-06-24

**Session:** Phase 1 review-and-merge · `cursor-agent/automated-pr-workflow-9b39`

## Duplicate & overlap groups

### personal-config — Palette ARIA dashboard

| Keep | Close | Overlap | Rationale |
| --- | --- | --- | --- |
| [#1340](https://github.com/abhimehro/personal-config/pull/1340) | [#1326](https://github.com/abhimehro/personal-config/pull/1326) | 2/3 files (`analytics_dashboard.sh`, `performance_optimizer.sh`) | #1340 is newer, narrower diff; #1326 also touched `.codacy.yml` |

### ctrld-sync — Bolt `_display_len` fast-path

| Keep | Close | Overlap | Rationale |
| --- | --- | --- | --- |
| [#947](https://github.com/abhimehro/ctrld-sync/pull/947) | [#946](https://github.com/abhimehro/ctrld-sync/pull/946) | 100% (`main.py`, `.jules/bolt.md`) | #947 newer; #946 failed CodeScene |

### ctrld-sync — error_messages rename

| Keep | Close | Overlap | Rationale |
| --- | --- | --- | --- |
| [#943](https://github.com/abhimehro/ctrld-sync/pull/943) (merged) | [#944](https://github.com/abhimehro/ctrld-sync/pull/944) | same lint fix | #943 merged first; #944 mypy-stale |

### Hydrograph — pyproject.toml mypy duplicates

| Keep | Close | Overlap | Rationale |
| --- | --- | --- | --- |
| [#295](https://github.com/abhimehro/Hydrograph_Versus_Seatek_Sensors_Project/pull/295) (merged) | [#293](https://github.com/abhimehro/Hydrograph_Versus_Seatek_Sensors_Project/pull/293) | pyproject.toml | #295 includes cleanup + Sentinel path guard; #293 was draft |

## Zero-diff / stale closures

| Repo | PR | Action | Reason |
| --- | ---: | --- | --- |
| Seatek_Analysis | 362 | CLOSE | Daily QA, 0 files changed |
| email-security-pipeline | 1148 | CLOSE | Daily QA healthy, 0 files changed |
| series_correction | 144 | CLOSE | Reverted formatting commits → net zero diff |
| series_correction | 148 | CLOSE | Daily QA, 0 files changed |

## Escalation clusters

### personal-config — Codacy infra (T0)

- **Symptom:** Every open PR fails `Codacy Security Scan` (cancel/fail) while other checks pass.
- **Continuity:** Same cluster as 2026-06-23 session after #1331 merge.
- **Disposition:** ESCALATE to Salvage/infra-fix; do not merge until Codacy gate recovers.

### repoprompt-ce — Style + security salvage cluster

- **PRs:** #24, #25, #41 (salvage), #42–46 (dependabot), #49, #51, #52
- **Symptom:** `Style`, `build`, `Build and Test`, `Codacy Security Scan`, `snyk` failures across cluster.
- **Disposition:** DEFER to Phase 2 Salvage; #41 remains security-tier ESCALATE.

### ctrld-sync — dependabot stale-branch mypy/ruff

- **PRs:** #938–942
- **Symptom:** mypy/ruff fail on dependabot branches predating #943/#947 merges.
- **Action taken:** `@dependabot rebase` posted on all five PRs.
- **Disposition:** Re-check next session after rebase CI completes.

## Merge ordering applied

1. SECURITY: Hydrograph #295, series_correction #146
2. CI/INFRA: ctrld #943 (unblocked dependabot tail)
3. PERFORMANCE/UI: ctrld #947 (auto-fix), esp #1144, series #150

## Stale threshold (30 days)

No PRs exceeded 30-day stale threshold at session start. Oldest in-scope: repoprompt-ce #24/#25 (4 days).
