# PR Triage — 2026-07-31

Phase 1 cron (`0 13 * * *`). Preflight PASS 7/7. Auth: GitHub token with close/merge permissions. Adversarial: opus-4.8 + gpt-5.5 parallel.

## Disposition summary

| Disposition | Count (planned) |
| --- | ---: |
| MERGE | ~22 |
| DEFER / twin | ~15 |
| REQUEST_CHANGES | ~6 |
| ESCALATE | ~8 |
| CONFLICTING → Phase 2 | ~9 |

## MERGE (consensus, CI green)

| Repo | PR | Why |
| --- | ---: | --- |
| personal-config | 1839 | Zero-diff Daily QA |
| personal-config | 1850 | CodeQL pin v4.37.4 SHA verified |
| personal-config | 1854 | Bolt regex twin (preferred over #1853/#1826/#1818) |
| personal-config | 1831 | defaultdict(list) equivalent |
| personal-config | 1846 | Brewfile + gh |
| personal-config | 1842 | zsh starter |
| personal-config | 1843 | git starter |
| personal-config | 1844 | nvim starter |
| personal-config | 1847 | gh extensions installer |
| personal-config | 1848 | wire bootstrap into setup.sh |
| ctrld-sync | 1089 | allowlist opt + test format (preferred over #1087) |
| ctrld-sync | 1083 | Partial batch status logging |
| Seatek_Analysis | 567 | Zero-diff Daily QA |
| Seatek_Analysis | 561 | named-fn extract (preferred over #569) |
| Hydrograph… | 446 | redundant dropna removal |
| Hydrograph… | 440 | pandas-stubs 3.x (dev) |
| Hydrograph… | 443 | scipy 1.18.0 |
| Hydrograph… | 442 | matplotlib 3.11.1 |
| series_correction… | 331 | fallback test only |
| series_correction… | 326 | helper extraction |
| series_correction… | 323 | JSON parse fix (`dummy_todos.py` only; no auth) |
| series_correction… | 321 | flatten `_get_data_directory` |
| repoprompt-ce | 162 | static DateFormatter |

## ESCALATE (security / trust boundary)

| Repo | PR | Reason |
| --- | ---: | --- |
| personal-config | 1822 | Sentinel CORS (archived alldebrid-server) |
| personal-config | 1841 | Sentinel timeout/auth env on subprocess |
| Seatek_Analysis | 568 | Sentinel path-hijacking (`shutil.which`) |
| Seatek_Analysis | 555 | Untrusted workspace_roots in 1Password/Copilot hook |
| Seatek_Analysis | 552 | Command injection (CONFLICTING) |
| Hydrograph… | 445 | Sentinel path traversal on `--output` |
| repoprompt-ce | 147 | Privileged workflows under "remove prints" title |
| repoprompt-ce | 158 | TOCTOU Sentinel (CI failing) |

## REQUEST_CHANGES

| Repo | PR | Reason |
| --- | ---: | --- |
| ctrld-sync | 1086 | Stray `pr_payload.json` |
| ctrld-sync | 1081 | test CI fail; repo-health |
| Seatek_Analysis | 560 | Scope creep (workflow/model + mclapply) |
| series_correction… | 337 | Alters NaN masking / outlier stats; journal wipe |
| personal-config | 1825 | Scratch `patch3.diff` / `scratch_triage.py` |
| repoprompt-ce | 144/148/152/156/157/159/161 | Failing Style/Build or huge merge-base noise |

## DEFER (twins / conflicts / large)

- pc #1853, #1830, #1826, #1818 — regex twins of #1854
- pc #1840, #1835, #1824, #1823 — CONFLICTING → Phase 2
- pc #1852 — large maintenance consolidate (human review)
- ctrld #1087 — subsumed by #1089; #1088 CodeScene (post `/cs-agent`)
- seatek #569 twin of #561; #563 zero-diff misleading title; #554 CONFLICTING
- series #336, #322 CONFLICTING/FAIL
- hg #441 — numpy 2.2→2.4 runtime bump (defer; not auto-merge majors)
- esp #1394 — large god-module split (human/Phase 2)
- rpce huge Palette/salvage diffs

## Prefer-twin map

| Group | Keep | Drop/defer |
| --- | --- | --- |
| pc regex PR extraction | #1854 | #1853, #1830, #1826, #1818 |
| ctrld allowlist | #1089 | #1087, #1086 (junk) |
| seatek metrics | #561 | #569 |
| rpce DateFormatter | #162 | #156 (CI fail, huge) |
