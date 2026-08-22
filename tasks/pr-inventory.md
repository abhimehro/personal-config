# PR Inventory — 2026-08-17 (Phase 1 review-and-merge)
# PR Inventory — 2026-08-18 (Phase 2 salvage)

Phase 2 cron (17:00 UTC). Preflight PASS. Auth: `abhimehro` PAT. Mode: salvage
(draft PRs only; **S1 never merge**).

Live re-fetch: **77** open, **13 CONFLICTING**. Input: Phase 1 remainder from
`pr-review-2026-08-16.md` + PR #2016 (`pr-review-2026-08-17.md`).

## Start-of-session CONFLICTING

| Repo                    | PR    | Head                                    | Salvage result            |
| ----------------------- | ----- | --------------------------------------- | ------------------------- |
| ctrld-sync              | #1188 | `jules/uv-docker-bandit-hardening-y4f4` | CLOSE → draft #1194       |
| ctrld-sync              | #1174 | `copilot/add-is-valid-rule-fn`          | CLOSE → draft #1195       |
| ctrld-sync              | #1161 | `jules/fix-network-timeout-retry-3k3t`  | HOLD 0fo                  |
| ctrld-sync              | #1136 | `copilot/update-mypy-2-x`               | ESCALATE                  |
| personal-config         | #2007 | `copilot/replace-eval-with-shopt-u`     | ESCALATE 0fu (no salvage) |
| personal-config         | #2000 | `jules/pgrep-cwe88-hardening-3j5k`      | CLOSE → draft #2022       |
| personal-config         | #1997 | `jules/bolt-join-hardening-x9k2`        | CLOSE (superseded #1996)  |
| personal-config         | #1991 | `copilot/palette-morning-brief-ux`      | CLOSE (superseded #1980)  |
| personal-config         | #1989 | `copilot/fix-pgrep-cwe-88-injection`    | CLOSE (superseded #2022)  |
| personal-config         | #1985 | `copilot/harden-bolt-join-lookup`       | CLOSE (superseded #1996)  |
| personal-config         | #1907 | `copilot/add-cors-whitelist-to-scripts` | ESCALATE                  |
| email-security-pipeline | #1495 | `copilot/add-daily-qa-workflow`         | CLOSE 0fr                 |
| email-security-pipeline | #1487 | `jules/security-headers-hardening-k9m2` | CLOSE (already on main)   |
| email-security-pipeline | #1473 | `jules/requirements-ci-default-5n8p`    | ESCALATE                  |
| Seatek_Analysis         | #690  | `copilot/fix-posixct-comparison-type`   | CLOSE → draft #693        |

## Drafts opened this run

| Repo            | PR    | Branch                                               |
| --------------- | ----- | ---------------------------------------------------- |
| personal-config | #2022 | `cursor-agent/salvage-pc-2000-pgrep-cwe88-517a`      |
| ctrld-sync      | #1194 | `cursor-agent/salvage-ctrld-1188-uv-docker-517a`     |
| ctrld-sync      | #1195 | `cursor-agent/salvage-ctrld-1174-is-valid-rule-517a` |
| Seatek_Analysis | #693  | `cursor-agent/salvage-seatek-690-posixct-517a`       |

## Merge-ready leftovers (human squash; not Phase 2)

| Repo               | PR    | Note                              |
| ------------------ | ----- | --------------------------------- |
| ctrld-sync         | #1194 | first (Docker/bandit + CI repair) |
| ctrld-sync         | #1195 | second (is_valid_rule)            |
| personal-config    | #2022 | pgrep CWE-88                      |
| Seatek_Analysis    | #693  | .POSIXct one-liner                |
| personal-config    | #1980 | Palette UX (keep; #1991 closed)   |
| personal-config    | #1996 | Bolt join CLEAN                   |
| personal-config    | #2016 | Phase 1 13:00 08-17 docs          |
| Hydrograph…        | #511  | hydro salvage leftover            |
| series_correction… | #393  | pytest skip                       |

---

# PR Inventory — 2026-08-13 (Phase 2 salvage)

Cron 13:00 UTC. Preflight PASS 7/7. Auth: `abhimehro` PAT. Stale: 30 days.
Adversarial: claude-opus-5-thinking-high + gpt-5.6-sol-high.

Live fetch (not the 2026-08-16 snapshot): **72** open, **71** auto/automation,
**1** human OOS (`pc#1969`).

## Start-of-session auto-open

| Repo                    | Auto open |
| ----------------------- | --------: |
| personal-config         |        14 |
| ctrld-sync              |        13 |
| email-security-pipeline |         5 |
| Seatek_Analysis         |        14 |
| Hydrograph…             |         7 |
| series_correction…      |         4 |
| repoprompt-ce           |        15 |
| **Total**               |    **72** |

## End-of-session open

| Repo                    |   Open |
| ----------------------- | -----: |
| personal-config         |     14 |
| ctrld-sync              |      8 |
| email-security-pipeline |      3 |
| Seatek_Analysis         |     13 |
| Hydrograph…             |      7 |
| series_correction…      |      3 |
| repoprompt-ce           |     14 |
| **Total**               | **62** |

## Inventory (start)

| Repo | PR | Author / pattern | Category | CI / merge | Age | Disposition |
| ---- | -- | ---------------- | -------- | ---------- | --- | ----------- |
| pc | [2014](https://github.com/abhimehro/personal-config/pull/2014) | Palette | UI | CLEAN | 1d | REQUEST_CHANGES (0ft) |
| pc | [2007](https://github.com/abhimehro/personal-config/pull/2007) | Sentinel CWE-78 | SECURITY | DIRTY | 2d | ESCALATE |
| pc | [2000](https://github.com/abhimehro/personal-config/pull/2000) | Sentinel CWE-88 | SECURITY | DIRTY | 3d | ESCALATE |
| pc | [1998](https://github.com/abhimehro/personal-config/pull/1998) | Sentinel CWE-1236 | SECURITY | CLEAN | 3d | ESCALATE |
| pc | [1997](https://github.com/abhimehro/personal-config/pull/1997) | Bolt join | PERFORMANCE | DIRTY | 3d | HOLD 0fo |
| pc | [1996](https://github.com/abhimehro/personal-config/pull/1996) | Bolt join | PERFORMANCE | CLEAN RC | 3d | HOLD 0fo |
| pc | [1991](https://github.com/abhimehro/personal-config/pull/1991) | Palette HTML | UI | DIRTY | 4d | HOLD |
| pc | [1989](https://github.com/abhimehro/personal-config/pull/1989) | Sentinel CWE-88 | SECURITY | DIRTY | 4d | ESCALATE |
| pc | [1985](https://github.com/abhimehro/personal-config/pull/1985) | Bolt join | PERFORMANCE | DIRTY | 5d | HOLD 0fo |
| pc | [1982](https://github.com/abhimehro/personal-config/pull/1982) | yaml skipIf | CI/INFRA | CLEAN RC | 5d | HOLD fail-open |
| pc | [1980](https://github.com/abhimehro/personal-config/pull/1980) | Sentinel SSRF | SECURITY | UNSTABLE CodeScene | 5d | ESCALATE |
| pc | [1978](https://github.com/abhimehro/personal-config/pull/1978) | Bolt join | PERFORMANCE | CLEAN | 5d | HOLD 0fo |
| pc | [1969](https://github.com/abhimehro/personal-config/pull/1969) | human feat | FEATURE | UNSTABLE Gitleaks | 13d | OOS human |
| pc | [1907](https://github.com/abhimehro/personal-config/pull/1907) | Sentinel CORS | SECURITY | DIRTY | 13d | ESCALATE |
| ctrld | [1192](https://github.com/abhimehro/ctrld-sync/pull/1192) | Devin skill | CI/INFRA | CLEAN | hours | **MERGED** |
| ctrld | [1191](https://github.com/abhimehro/ctrld-sync/pull/1191) | Devin blueprint | CI/INFRA | CLEAN 0-diff | hours | **CLOSED** |
| ctrld | [1190](https://github.com/abhimehro/ctrld-sync/pull/1190) | Devin skill | CI/INFRA | CLEAN | hours | **MERGED** |
| ctrld | [1189](https://github.com/abhimehro/ctrld-sync/pull/1189) | Devin blueprint | CI/INFRA | CLEAN typo | hours | **CLOSED** |
| ctrld | [1188](https://github.com/abhimehro/ctrld-sync/pull/1188) | Devin uv | CI/INFRA | DIRTY | hours | DEFER P2 |
| ctrld | [1187](https://github.com/abhimehro/ctrld-sync/pull/1187) | Devin settings | FEATURE | CLEAN | hours | ESCALATE |
| ctrld | [1185](https://github.com/abhimehro/ctrld-sync/pull/1185) | test typing | REFACTOR | CLEAN | 1d | **MERGED** |
| ctrld | [1174](https://github.com/abhimehro/ctrld-sync/pull/1174) | Sentinel | SECURITY | DIRTY | 2d | ESCALATE |
| ctrld | [1170](https://github.com/abhimehro/ctrld-sync/pull/1170) | Dependabot gh-aw | DEPENDENCY | CLEAN RC | 3d | HOLD floating tag |
| ctrld | [1165](https://github.com/abhimehro/ctrld-sync/pull/1165) | QA mypy | CI/INFRA | CLEAN | 4d | HOLD (human QA) |
| ctrld | [1161](https://github.com/abhimehro/ctrld-sync/pull/1161) | Bolt sum | PERFORMANCE | DIRTY | 5d | HOLD 0fo |
| ctrld | [1156](https://github.com/abhimehro/ctrld-sync/pull/1156) | Sentinel TOCTOU | SECURITY | CLEAN | 7d | ESCALATE |
| ctrld | [1136](https://github.com/abhimehro/ctrld-sync/pull/1136) | Dependabot mypy 2.x | DEPENDENCY | DIRTY | 10d | ESCALATE major |
| esp | [1492](https://github.com/abhimehro/email-security-pipeline/pull/1492) | Palette colors | UI | CLEAN | 1d | **MERGED** |
| esp | [1490](https://github.com/abhimehro/email-security-pipeline/pull/1490) | repo-health stubs | REFACTOR | CLEAN | 1d | **MERGED** |
| esp | [1487](https://github.com/abhimehro/email-security-pipeline/pull/1487) | Bolt headers | PERFORMANCE | DIRTY | 1d | DEFER P2 |
| esp | [1473](https://github.com/abhimehro/email-security-pipeline/pull/1473) | Cursor health | CI/INFRA | CLEAN | 4d | ESCALATE |
| esp | [1444](https://github.com/abhimehro/email-security-pipeline/pull/1444) | Dependabot opencv 5 | DEPENDENCY | UNSTABLE | 7d | ESCALATE major |
| seatek | [686](https://github.com/abhimehro/Seatek_Analysis/pull/686) | Bolt mean.default | PERFORMANCE | CLEAN | 1d | HOLD |
| seatek | [685](https://github.com/abhimehro/Seatek_Analysis/pull/685) | Palette CLI | UI | CLEAN | 1d | REQUEST_CHANGES |
| seatek | [684](https://github.com/abhimehro/Seatek_Analysis/pull/684) | CI consolidate | CI/INFRA | CLEAN | 1d | ESCALATE |
| seatek | [681](https://github.com/abhimehro/Seatek_Analysis/pull/681) | Bolt mean.default | PERFORMANCE | CLEAN | 1d | **CLOSED** dup |
| seatek | [680](https://github.com/abhimehro/Seatek_Analysis/pull/680) | Sentinel DoS | SECURITY | CLEAN | 1d | ESCALATE |
| seatek | [679](https://github.com/abhimehro/Seatek_Analysis/pull/679) | Palette CLI | UI | CLEAN | 1d | REQUEST_CHANGES |
| seatek | [676](https://github.com/abhimehro/Seatek_Analysis/pull/676) | Sentinel DoS | SECURITY | CLEAN | 2d | ESCALATE |
| seatek | [673](https://github.com/abhimehro/Seatek_Analysis/pull/673) | Daily QA lint | REFACTOR | CLEAN RC | 2d | REQUEST_CHANGES |
| seatek | [667](https://github.com/abhimehro/Seatek_Analysis/pull/667) | Sentinel encoding | SECURITY | CLEAN | 3d | ESCALATE |
| seatek | [665](https://github.com/abhimehro/Seatek_Analysis/pull/665) | Sentinel DoS | SECURITY | CLEAN | 4d | ESCALATE |
| seatek | [662](https://github.com/abhimehro/Seatek_Analysis/pull/662) | Sentinel encoding | SECURITY | CLEAN | 5d | ESCALATE |
| seatek | [661](https://github.com/abhimehro/Seatek_Analysis/pull/661) | Dependabot numpy 2.5 | DEPENDENCY | UNSTABLE | 6d | ESCALATE major |
| seatek | [657](https://github.com/abhimehro/Seatek_Analysis/pull/657) | Sentinel yaml | SECURITY | CLEAN | 7d | ESCALATE |
| seatek | [643](https://github.com/abhimehro/Seatek_Analysis/pull/643) | Cursor untrack | CI/INFRA | UNSTABLE mega | 7d | ESCALATE |
| hg | [528](https://github.com/abhimehro/Hydrograph_Versus_Seatek_Sensors_Project/pull/528) | Sentinel path | SECURITY | CLEAN | 1d | ESCALATE |
| hg | [526](https://github.com/abhimehro/Hydrograph_Versus_Seatek_Sensors_Project/pull/526) | Sentinel path | SECURITY | CLEAN | 1d | ESCALATE |
| hg | [524](https://github.com/abhimehro/Hydrograph_Versus_Seatek_Sensors_Project/pull/524) | Sentinel path | SECURITY | CLEAN | 2d | ESCALATE |
| hg | [523](https://github.com/abhimehro/Hydrograph_Versus_Seatek_Sensors_Project/pull/523) | QA black | REFACTOR | CLEAN RC | 2d | HOLD 0fg |
| hg | [520](https://github.com/abhimehro/Hydrograph_Versus_Seatek_Sensors_Project/pull/520) | Sentinel path | SECURITY | CLEAN | 2d | ESCALATE |
| hg | [507](https://github.com/abhimehro/Hydrograph_Versus_Seatek_Sensors_Project/pull/507) | salvage | SECURITY | CLEAN | 5d | ESCALATE (draft path) |
| hg | [498](https://github.com/abhimehro/Hydrograph_Versus_Seatek_Sensors_Project/pull/498) | Cursor health | CI/INFRA | UNSTABLE | 7d | ESCALATE |
| series | [400](https://github.com/abhimehro/series_correction_project_updated/pull/400) | Daily QA | CI/INFRA | CLEAN 0-diff | 1d | **CLOSED** |
| series | [393](https://github.com/abhimehro/series_correction_project_updated/pull/393) | Dependabot numpy | DEPENDENCY | UNSTABLE | 3d | ESCALATE major |
| series | [390](https://github.com/abhimehro/series_correction_project_updated/pull/390) | Bolt shallow copy | PERFORMANCE | CLEAN | 4d | HOLD 0fp |
| series | [386](https://github.com/abhimehro/series_correction_project_updated/pull/386) | Dependabot pandas 3 | DEPENDENCY | UNSTABLE | 6d | ESCALATE major |
| rpce | [261](https://github.com/abhimehro/repoprompt-ce/pull/261) | Bolt DateFormatter | PERFORMANCE | CLEAN | hours | HOLD concurrency |
| rpce | [260](https://github.com/abhimehro/repoprompt-ce/pull/260) | Palette a11y | UI | CLEAN | 1d | **MERGED** |
| rpce | [258](https://github.com/abhimehro/repoprompt-ce/pull/258) | Sentinel TOCTOU | SECURITY | CLEAN | 1d | ESCALATE |
| rpce | [257](https://github.com/abhimehro/repoprompt-ce/pull/257) | Bolt | PERFORMANCE | UNSTABLE | 1d | HOLD |
| rpce | [254](https://github.com/abhimehro/repoprompt-ce/pull/254) | Sentinel TOCTOU | SECURITY | UNSTABLE | 2d | ESCALATE |
| rpce | [253](https://github.com/abhimehro/repoprompt-ce/pull/253) | Palette a11y | UI | UNSTABLE RC | 3d | HOLD junk |
| rpce | [250](https://github.com/abhimehro/repoprompt-ce/pull/250) | Sentinel TOCTOU | SECURITY | UNSTABLE | 3d | ESCALATE |
| rpce | [249](https://github.com/abhimehro/repoprompt-ce/pull/249) | Bolt DateFormatter | PERFORMANCE | UNSTABLE | 3d | HOLD |
| rpce | [247](https://github.com/abhimehro/repoprompt-ce/pull/247) | Palette a11y | UI | CLEAN RC | 4d | HOLD junk |
| rpce | [244](https://github.com/abhimehro/repoprompt-ce/pull/244) | salvage tests | FEATURE | UNSTABLE | 4d | ESCALATE (no merge) |
| rpce | [243](https://github.com/abhimehro/repoprompt-ce/pull/243) | Sentinel TOCTOU | SECURITY | UNSTABLE | 4d | ESCALATE |
| rpce | [241](https://github.com/abhimehro/repoprompt-ce/pull/241) | Bolt DateFormatter | PERFORMANCE | UNSTABLE | 4d | HOLD |
| rpce | [239](https://github.com/abhimehro/repoprompt-ce/pull/239) | Sentinel TOCTOU | SECURITY | UNSTABLE | 5d | ESCALATE |
| rpce | [237](https://github.com/abhimehro/repoprompt-ce/pull/237) | salvage tests | FEATURE | UNSTABLE | 5d | ESCALATE (no merge) |
| rpce | [236](https://github.com/abhimehro/repoprompt-ce/pull/236) | Bolt DateFormatter | PERFORMANCE | UNSTABLE | 5d | HOLD |
