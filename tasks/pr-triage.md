# PR triage — automated PR review agent (review-and-merge)

**Preflight:** `bash scripts/preflight-gh-pr-automation.sh --config tasks/pr-review-agent.config.yaml` — **passed** (read-only); expected `viewerCanEnableAutoMerge=false` warnings.

## Historical triage — 2026-03-27 (archived)

| Repo | PR # | Category | Duplicate / stale | Disposition | Rationale |
| ---- | ---: | -------- | ----------------- | ----------- | --------- |
| personal-config | 682 | SECURITY | None | **MERGED** (squash) | CWE-377 LaunchAgent log paths; checks green. **Auto-fix:** restored `.trunk/plugins/trunk` symlink to match `main` (Jules had pointed it at a runner-local path). |
| personal-config | 681 | CI/INFRA | None | **ESCALATE / hold** | Merge conflicts with `main`; daily QA batch — human rebase + review. |
| personal-config | 678 | CI/INFRA | None | **ESCALATE** | Draft workflow consolidation — CI trust boundary; verify action pins and `permissions:`. |
| personal-config | 677 | SECURITY | Superseded by #682 | **CLOSED** | Same plist fix as #682; redundant sentinel doc + conflicts. |
| ctrld-sync | 672 | SECURITY | None | **MERGED** | URL length cap in `validate_folder_url`; checks green. |
| ctrld-sync | 669 | CI/INFRA | None | **ESCALATE** | Draft workflow consolidation. |
| ctrld-sync | 668 | SECURITY | Superseded by #672 | **CLOSED** | Same URL limit intent; conflicting + #672 merged. |
| email-security-pipeline | 587 | CI/INFRA | None | **MERGED** | Fix invalid `<version>` placeholder in pre-commit config; checks green. |
| email-security-pipeline | 592 | PERFORMANCE | None | **MERGED** | File signature detection optimization; checks green. |
| email-security-pipeline | 596 | UI | None | **MERGED** | CLI spinner / a11y; checks green. |
| email-security-pipeline | 597 | SECURITY | None | **MERGED** | Attachment detection bypass; checks green; merge before closing #585. |
| email-security-pipeline | 594 | CI/INFRA | None | **ESCALATE** | Draft; 14 workflow files — human review required. |
| email-security-pipeline | 593 | CI/INFRA | No-op | **CLOSED** | `changedFiles == 0`; QA narrative only. |
| email-security-pipeline | 585 | SECURITY | Obsolete vs main after #597 | **CLOSED** | Conflicted; superseded by merged attachment hardening. |
| Seatek_Analysis | 106 | SECURITY | None | **MERGED** | Redact exception details in logs; checks green. |
| Seatek_Analysis | 107 | PERFORMANCE | None | **MERGED** | Vectorized correction application; checks green (merged after #106). |
| Hydrograph_Versus_Seatek_Sensors_Project | 93 | PERFORMANCE | None | **MERGED** | Micro-optimizations; checks green. |
| Hydrograph_Versus_Seatek_Sensors_Project | 94 | SECURITY | None | **MERGED** | Centralize `sanitize_filename`; checks green (merged after #93). |

### Merge ordering — 2026-03-27 (executed)

1. email-security-pipeline: 587 → 592 → 596 → 597 (dependency/UI before security parser change).
2. personal-config: 682 (after symlink fix).
3. ctrld-sync: 672.
4. Seatek_Analysis: 106 → 107.
5. Hydrograph: 93 → 94.

---

## Triage — 2026-04-01 (this run)

| Repo | PR # | Category | Duplicate / notes | Disposition | Rationale |
| ---- | ---: | -------- | ----------------- | ----------- | --------- |
| Seatek_Analysis | 114 | PERFORMANCE + fix | Fixes `main` F821 (`BytesIO` undefined) | **MERGED** (squash) | Required for green `validate` on Dependabot PRs; security-adjacent but mechanical import |
| Seatek_Analysis | 115 | DEPENDENCY | None | **MERGED** (squash) | `actions/setup-python` bump; `validate` failure traced to **pre-merge `main`** bug, not PR diff |
| Seatek_Analysis | 116 | DEPENDENCY | None | **MERGED** (squash) | `actions/checkout` bump; same rationale as #115 |
| Seatek_Analysis | 117 | SECURITY | None | **MERGED** (squash) | CLI option injection hardening; CI green |
| Seatek_Analysis | 119 | SECURITY | None | **MERGED** (squash) | Changelog workflow injection fix; CI green |
| Seatek_Analysis | 118 | PERFORMANCE | Superseded by #114 (+ same code path) | **CLOSED** | Redundant with merged #114; could not push merge commit to PR branch (git credential used `cursor[bot]` — see lessons) |
| email-security-pipeline | 617 | PERFORMANCE | Preferred over #611 | **MERGED** (squash) | Newer Laplacian optimization PR |
| email-security-pipeline | 616 | UI | None | **MERGED** (squash) | `submit-pypi` failed with GitHub **HttpError** on dependency snapshot API — **unrelated** to PR code; other checks green |
| email-security-pipeline | 611 | PERFORMANCE | Duplicate of #617 | **CLOSED** | Superseded by #617 |
| email-security-pipeline | 618 | CI/INFRA | No-op | **CLOSED** | `changedFiles == 0` |
| email-security-pipeline | 614 | PERFORMANCE | Conflicts after #617 | **HOLD** | `mergeable=CONFLICTING`; CodeScene previously flagged complexity — comment left, no merge |
| Hydrograph_Versus_Seatek_Sensors_Project | 97 | SECURITY | None | **MERGED** (squash) | Path traversal fix in test processor; CI green |
| Hydrograph_Versus_Seatek_Sensors_Project | 98 | PERFORMANCE | None | **MERGED** (squash) | Boolean masking micro-opts; merged after #97 |
| personal-config | 701 | SECURITY | None | **MERGED** (squash) | Sentinel fix; CI green |
| personal-config | 699 | PERFORMANCE | None | **MERGED** (squash) | Bolt I/O optimization; CI green |
| personal-config | 703 | CI/INFRA | None | **MERGED** (squash) | Jules daily QA TOML/format; CI green |
| personal-config | 697 | CI/INFRA | None | **ESCALATE** | Draft workflow consolidation — human security review |
| ctrld-sync | 687 | CI/INFRA | None | **ESCALATE** | Draft + **failing** ruff/mypy/test |
| email-security-pipeline | 612 | CI/INFRA | None | **ESCALATE** | Draft workflow consolidation — 14 files |

### Merge ordering — 2026-04-01 (executed)

1. Seatek: **114** → **115** → **116** → **117** → **119** (fix base, then deps, then security).
2. email: **617** → close **611**/**618** → **616**.
3. Hydro: **97** → **98**.
4. personal-config: **701** → **699** → **703**.
5. Seatek: close **118** (superseded).

## Automation expansion (policy)

Include when **any** of: `author.is_bot`, Dependabot branch prefix, branch matches `jules/*`, `sentinel-*`, `bolt/*`, `palette/*`, `automation-*`, `daily-qa-*`, `chore/jules-*`, `fix/toml-*` with Jules title, or PR comments from `google-labs-jules`.
