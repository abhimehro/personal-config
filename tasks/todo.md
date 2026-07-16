# ABHI-1135 — CI caching for ShellCheck and Trunk

## Approach

Centralize install+cache in reusable composite actions (DRY across workflows), pin tool versions for supply-chain + cache invalidation, replace apt installs with cached binaries.

**Trust boundary:** Cache restores untrusted blobs from GitHub Actions cache; mitigate by pinning download URLs to known versions and validating version input allowlists. Prefer SHA-pinned `actions/cache`.

**Security:** No secrets in cache keys/paths. Validate version strings before interpolating into download URLs. Do not weaken existing lint gates.

## Checklist

- [x] Create `.github/actions/setup-shellcheck` (cache + pinned binary install)
- [x] Create `.github/actions/setup-trunk` (cache `~/.cache/trunk` + CLI launcher)
- [x] Wire into: `code-quality.yml`, `shellcheck.yml`, `mac-audit.yml`, `security-scan.yml`, `repository-automation-daily.yml`, `daily-perf-improver/build-steps`
- [x] Align `ci-performance.md` with actual implementation
- [x] Validate YAML; smoke-test ShellCheck install (`tests/test_setup_shellcheck_action.sh` 7/7)
- [x] Commit, push, open draft PR; comment on Linear ABHI-1135
  - PR: https://github.com/abhimehro/personal-config/pull/1669
