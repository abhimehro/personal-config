# PR Triage — 2026-07-14 (evening salvage)

**Session:** Automated PR salvage & cleanup (cron 17:00 UTC)  
**Mode:** Phase 2 salvage  
**Preflight:** PASS 6/6 + repoprompt-ce

## Decision matrix

| Decision | Count | PRs |
|----------|------:|-----|
| RECONCILE (drop — resolved by Phase 1) | 4 | pc #1593, #1602; hg #344, #355 |
| ESCALATE (carry) | 3 | cs #990; sc #210; rpce #112 |
| ESCALATE (new) | 1 | esp #1259 |
| DEFER (new → Phase 1) | 5 | pc #1609, #1610; cs #1011; esp #1260; hg #357 |
| SALVAGE DRAFT | 0 | — |
| CLOSE | 0 | — |
| MERGE | 0 | Policy S1 — salvage never merges |

## Security gates

| PR | Gate | Rationale |
|----|------|-----------|
| cs #990 | **ESCALATE** | SSRF domain allowlist trust boundary; benchmark regression from validation overhead |
| sc #210 | **ESCALATE** | CLI exception output sanitization at trust boundary (Lesson 0de) |
| rpce #112 | **ESCALATE** | Ephemeral URLSession / persisted token leak (Lesson 0de) |
| esp #1259 | **ESCALATE** | Dependency pinning on security-classified repo (Lesson 0bb) |
| cs #1011 | PASS | Palette prompt formatting only |
| esp #1260 | PASS | Palette UX hierarchy only |
| hg #357 | PASS | Routine poetry.lock pin |

## cs #990 blocker detail

| Check | Status | Notes |
|-------|--------|-------|
| CodeScene | PASS | cs-agent remediation completed |
| test / mypy / bandit | PASS | Functional tests green |
| ruff | FAIL | 1 fixable blank-line whitespace (`main.py` ~2356) |
| benchmark | FAIL | 1.80× / 1.64× regression on `push_rules` benchmarks — SSRF validation cost |

## Deferred follow-ups

```yaml
open_followups:
  - repo: abhimehro/ctrld-sync
    pr: 990
    reason: ESCALATE — SSRF allowlist + benchmark trade-off
  - repo: abhimehro/series_correction_project_updated
    pr: 210
    reason: ESCALATE — CLI exception sanitization
  - repo: abhimehro/repoprompt-ce
    pr: 112
    reason: ESCALATE — URLSession token hardening
  - repo: abhimehro/email-security-pipeline
    pr: 1259
    reason: ESCALATE — supply-chain pin on security repo
  - repo: abhimehro/personal-config
    pr: 1609
    reason: DEFER — Devin maintenance; CI green
  - repo: abhimehro/personal-config
    pr: 1610
    reason: DEFER — Palette a11y; Swift CodeQL pending
  - repo: abhimehro/ctrld-sync
    pr: 1011
    reason: DEFER — Palette; CI green
  - repo: abhimehro/email-security-pipeline
    pr: 1260
    reason: DEFER — Palette UX; CI green
  - repo: abhimehro/Hydrograph_Versus_Seatek_Sensors_Project
    pr: 357
    reason: DEFER — Devin deps; CI green
```

---

# PR Triage — 2026-07-08

**Session:** Automated PR review & cleanup (cron 13:00 UTC)  
**Mode:** review-and-merge  
**Preflight:** PASS 6/6

## Decision matrix

| Decision | Count | PRs |
|----------|------:|-----|
| MERGE | 7 | pc #1542, #1539, #1545; Seatek #430; hg #330; sc #201 |
| CLOSE | 2 | pc #1540 (superseded draft); esp #1241 (no-op QA) |
| ESCALATE | 3 | pc #1544; cs #990; esp #1240 |
| DEFER | 5 | sc #204; rpce #100–#102, #105 |
