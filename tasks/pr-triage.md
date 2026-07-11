# PR Triage — 2026-07-11 (Phase 2 salvage)

**Session:** Automated PR salvage & cleanup (cron 17:00 UTC)  
**Mode:** salvage (Phase 2)  
**Preflight:** PASS 6/6

## Salvage decision matrix

| Decision | Count | PRs |
|----------|------:|-----|
| AUTO-RESOLVED | 1 | sc #214 (CodeScene cs-agent completed; all CI green) |
| HOLD ESCALATED | 4 | pc #1578, cs #990, sc #210, rpce #112 |
| SALVAGE DRAFT | 0 | — (no DIRTY/conflicted PRs; no infra-broken repos) |
| CLOSE SUPERSEDED | 0 | — |

## Conflict scan

Zero open PRs with merge conflicts across all 7 configured repos.

## Security gates (unchanged — human approval required)

| PR | Tier | Gate |
|----|------|------|
| [pc #1578](https://github.com/abhimehro/personal-config/pull/1578) | T1 | CWE-88 pkill/pgrep option injection |
| [cs #990](https://github.com/abhimehro/ctrld-sync/pull/990) | T1 | SSRF allowlist + benchmark CI red |
| [sc #210](https://github.com/abhimehro/series_correction_project_updated/pull/210) | T1 | CLI exception sanitization (salvage of #205) |
| [rpce #112](https://github.com/abhimehro/repoprompt-ce/pull/112) | T1 | Ephemeral URLSession for AI provider tokens |

## Auto-resolved

| PR | Was | Now | Next step |
|----|-----|-----|-----------|
| [sc #214](https://github.com/abhimehro/series_correction_project_updated/pull/214) | DEFER (CodeScene FAIL) | All checks SUCCESS | Phase 1 merge on next cycle |

```yaml
open_followups:
  - repo: abhimehro/personal-config
    pr: 1578
    reason: ESCALATE — CWE-88; human security review
  - repo: abhimehro/ctrld-sync
    pr: 990
    reason: ESCALATE — SSRF allowlist + benchmark fail
  - repo: abhimehro/series_correction_project_updated
    pr: 210
    reason: ESCALATE — CLI exception sanitization
  - repo: abhimehro/repoprompt-ce
    pr: 112
    reason: ESCALATE — URLSession credential persistence
  - repo: abhimehro/series_correction_project_updated
    pr: 214
    reason: MERGE-ELIGIBLE — CodeScene green; Phase 1 re-run
  - repo: abhimehro/personal-config
    pr: 1584
    reason: NEW — Palette a11y; triage next Phase 1
```

---

# PR Triage — 2026-07-11 (Phase 1)

**Session:** Automated PR review & cleanup (cron 13:00 UTC)  
**Mode:** review-and-merge  
**Preflight:** PASS 6/6

## Duplicate / overlap groups

| Group | Keep | Close / defer | Rationale |
|-------|------|---------------|-----------|
| Media server a11y (`infuse-media-server.py`) | [#1577](https://github.com/abhimehro/personal-config/pull/1577) | #1573, #1570 | Same semantic `<nav>/<ul>/<li>` intent; #1577 green CI + palette doc |
| CONTROLD_REPO test harness | [#1576](https://github.com/abhimehro/personal-config/pull/1576) | #1574 (draft) | Identical harness fix; Jules QA branch merged first |
| Session report docs | *(this session artifacts)* | #1569, #1572 | Prior cron/salvage reports superseded by 2026-07-11 session |
| Jules daily QA no-ops | — | #1252, #442, #213 | 0 file changes; tests already green on `main` |

## Security escalations (human approval required)

| PR | Concern | Gate |
|----|---------|------|
| [pc #1578](https://github.com/abhimehro/personal-config/pull/1578) | CWE-88 option injection in `pkill`/`pgrep` | Trust boundary — process management in VPN/DNS scripts |
| [cs #990](https://github.com/abhimehro/ctrld-sync/pull/990) | SSRF allowlist for blocklist fetches | Trust boundary + **benchmark CI failing** |
| [sc #210](https://github.com/abhimehro/series_correction_project_updated/pull/210) | CLI exception output sanitization | Information-disclosure boundary |
| [rpce #112](https://github.com/abhimehro/repoprompt-ce/pull/112) | Ephemeral `URLSessionConfiguration` for AI providers | Credential/cache persistence on disk |

## Auto-fix outcomes

| PR | Failure | Fix applied | Result |
|----|---------|-------------|--------|
| [pc #1571](https://github.com/abhimehro/personal-config/pull/1571) | `test_controld_validation.sh` missing `CONTROLD_REPO` | Merged `main` (#1576 harness) | CI green → **merged** |
| [pc #1581](https://github.com/abhimehro/personal-config/pull/1581) | SC2155 in harness + merge conflicts after #1571 | Split declare/assign; resolved `.jules/bolt.md` | CI green → **merged** |

## Deferred

| PR | Blocker | Next step |
|----|---------|-----------|
| [sc #214](https://github.com/abhimehro/series_correction_project_updated/pull/214) | CodeScene FAIL | `/cs-agent skill:fix-code-health-degradations` posted; await remediation |

## Merge ordering applied

1. Test harness fix (#1576) before dependent Palette/Bolt branches
2. Dependency bump (esp #1251) before feature PRs
3. CI/lint config (hv #340) before perf PRs
4. Security tooling (sa #439 bandit) before perf (sa #443)
5. Autofix salvage merges (#1571, #1581) after harness landed on `main`

---

# PR Triage — 2026-07-08
