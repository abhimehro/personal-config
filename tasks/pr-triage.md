# PR Triage — 2026-07-11

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
