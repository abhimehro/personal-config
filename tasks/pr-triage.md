# PR triage — 2026-04-01 (automated PR review agent, review-and-merge)

**Preflight:** `bash scripts/preflight-gh-pr-automation.sh --config tasks/pr-review-agent.config.yaml` — **passed** (read-only); expected `viewerCanEnableAutoMerge=false` warnings.

## Dispositions

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

## Merge ordering (executed)

1. Seatek: **114** → **115** → **116** → **117** → **119** (fix base, then deps, then security).  
2. email: **617** → close **611**/**618** → **616**.  
3. Hydro: **97** → **98**.  
4. personal-config: **701** → **699** → **703**.  
5. Seatek: close **118** (superseded).

## Automation expansion (policy)

Include when **any** of: `author.is_bot`, Dependabot branch prefix, branch matches `jules/*`, `sentinel-*`, `bolt/*`, `palette/*`, `automation-*`, `daily-qa-*`, `chore/jules-*`, `fix/toml-*` with Jules title, or PR comments from `google-labs-jules`.
