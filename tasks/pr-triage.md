# PR Triage — 2026-07-13 (evening salvage)

**Session:** Automated PR salvage & cleanup (cron 17:00 UTC)  
**Mode:** Phase 2 salvage  
**Preflight:** PASS 6/6 + cursor-cloud-hooks

## Decision matrix

| Decision | Count | PRs |
|----------|------:|-----|
| CLOSE (duplicate) | 1 | rpce #123 |
| CLOSE (superseded draft) | 1 | pc #1601 |
| ESCALATE (unchanged) | 4 | pc #1593; cs #990; sc #210; rpce #112 |
| DEFER (unchanged) | 1 | hg #344 |
| NEW OPEN (post-Phase 1) | 1 | pc #1602 |

## Security gates

| PR | Gate | Rationale |
|----|------|-----------|
| rpce #123 | **CLOSE** | Duplicate Sentinel URLSession fix; canonical #112 has test coverage + green CI |
| pc #1593 | **ESCALATE** | Unchanged — CWE-78 command injection in repair script |
| cs #990 | **ESCALATE** | Unchanged — SSRF allowlist + benchmark FAIL |
| sc #210 | **ESCALATE** | Unchanged — CLI exception sanitization salvage |
| rpce #112 | **ESCALATE** | Unchanged — URLSession ephemeral hardening |
| pc #1602 | **PASS** (pending CI) | Palette isatty guard only; no trust-boundary change |

## Duplicate resolution

### repoprompt-ce Sentinel URLSession cluster

- **Keep:** [#112](https://github.com/abhimehro/repoprompt-ce/pull/112) — canonical; includes `AgentRunWorktreeStartTests.swift`; all CI green
- **Closed:** [#123](https://github.com/abhimehro/repoprompt-ce/pull/123) — same-day duplicate missing tests

## Deferred follow-ups (EOD evening)

```yaml
open_followups:
  - repo: abhimehro/personal-config
    pr: 1602
    reason: NEW — Palette isatty; merge when CI green (Phase 1)
  - repo: abhimehro/personal-config
    pr: 1593
    reason: ESCALATE — Sentinel command injection; human security review
  - repo: abhimehro/ctrld-sync
    pr: 990
    reason: ESCALATE — SSRF allowlist + benchmark fail
  - repo: abhimehro/series_correction_project_updated
    pr: 210
    reason: ESCALATE — CLI exception sanitization; human approval
  - repo: abhimehro/repoprompt-ce
    pr: 112
    reason: ESCALATE — URLSession ephemeral hardening; human approval
  - repo: abhimehro/Hydrograph_Versus_Seatek_Sensors_Project
    pr: 344
    reason: DEFER — CodeScene FAIL; await cs-agent remediation
```

## Salvage assessment

No new salvage drafts required. Phase 1 tail PRs remain correctly gated. Infra-broken detection: **not triggered** (no 4+ PRs sharing same `main` failure).

---

# PR Triage — 2026-07-13

**Session:** Automated PR review & cleanup (cron 13:00 UTC)  
**Mode:** review-and-merge  
**Preflight:** PASS 6/6

## Decision matrix

| Decision | Count | PRs |
|----------|------:|-----|
| MERGE | 5 | pc #1600, #1598; cs #1005, #1004; sc #222 |
| CLOSE | 8 | pc #1597, #1594, #1592; hg #349, #351, #352; sc #221, #218 |
| ESCALATE | 4 | pc #1593; cs #990; sc #210; rpce #112 |
| DEFER | 1 | hg #344 |

## Security gates

| PR | Gate | Rationale |
|----|------|-----------|
| pc #1593 | **ESCALATE** | Sentinel CWE-78 command-injection fix in repair script; GH_TOKEN/subprocess trust boundary |
| cs #990 | **ESCALATE** | SSRF domain allowlist + benchmark CI red (unchanged from 2026-07-12) |
| sc #210 | **ESCALATE** | CLI exception output sanitization (salvage of #205) |
| rpce #112 | **ESCALATE** | URLSession ephemeral configuration across HTTP providers |
| cs #1005 | **MERGE** | TOCTOU hardening via `os.open`+`fchmod`; defensive fix, CI green, tests updated |
| All other merged PRs | PASS | No secrets added; no permission escalation; security scans green |

## Duplicate & overlap resolution

### Hydrograph Bolt min/max cluster

- **Keep:** [#344](https://github.com/abhimehro/Hydrograph_Versus_Seatek_Sensors_Project/pull/344) — oldest canonical branch; `/cs-agent` posted previously
- **Closed:** #351, #352 — semantic duplicates with CodeScene FAIL

### series_correction pandas C-engine

- **Merged:** [#222](https://github.com/abhimehro/series_correction_project_updated/pull/222) — newest Bolt branch, CodeScene green
- **Closed:** #218 — salvage duplicate superseded

### Jules daily QA no-ops (0 file changes)

- Closed: pc #1597, hg #349, sc #221

### Draft session-report PRs

- Closed: pc #1594 (salvage draft), #1592 (review draft) — superseded by `tasks/pr-review-2026-07-13.md`

## Deferred follow-ups

```yaml
open_followups:
  - repo: abhimehro/personal-config
    pr: 1593
    reason: ESCALATE — Sentinel command injection; human security review
  - repo: abhimehro/ctrld-sync
    pr: 990
    reason: ESCALATE — SSRF allowlist + benchmark fail
  - repo: abhimehro/series_correction_project_updated
    pr: 210
    reason: ESCALATE — CLI exception sanitization; human approval
  - repo: abhimehro/repoprompt-ce
    pr: 112
    reason: ESCALATE — URLSession ephemeral hardening; human approval
  - repo: abhimehro/Hydrograph_Versus_Seatek_Sensors_Project
    pr: 344
    reason: DEFER — CodeScene FAIL; await cs-agent remediation
```

## Salvage handoff

Phase 2 salvage trigger: **not required** — only 1 deferred PR (hg #344) with CodeScene failure; no 4+ PRs sharing same infra breakage.
