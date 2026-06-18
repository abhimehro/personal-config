# Security remediation plan — 2026-05-01

This plan converts the security/dependency audit into progressive work items.
Items are grouped so they can become GitHub issues once `gh` is
re-authenticated.

## Issue 1 — Rotate live local credentials and remove committed WebDAV examples

Priority: P0

### Context

- TruffleHog verified a live GitHub PAT in local `GH_TOKEN.env` (gitignored, not
  tracked).
- Media streaming docs contained hardcoded WebDAV `curl -u` examples.

### Done in current remediation batch

- Replaced committed WebDAV password examples with `${MEDIA_WEBDAV_PASS}`
  placeholders.
- Confirmed `npm audit` for `copilot-demo` now reports 0 vulnerabilities.
- Confirmed repo grep no longer finds the hardcoded WebDAV password.

### Remaining manual actions

- Rotate/revoke the GitHub PAT in GitHub settings.
- Rotate the WebDAV password in 1Password/media-server configuration (run
  `./media-streaming/scripts/rotate-media-webdav.sh` on macOS with `op` signed
  in; see `docs/CREDENTIAL_ROTATION.md`).
- Decide whether repository history needs purging for the old WebDAV password.

### Acceptance criteria

- `trufflehog filesystem . --only-verified` returns no verified secrets.
- `grep -R "curl -u \"infuse:" media-streaming` only shows placeholder-based
  examples.
- Any rotated secrets are no longer stored inside the repo root.

## Issue 2 — Harden GitHub Actions supply chain

Priority: P1

### Context

Audit found unpinned actions/images, broad permissions, and some malformed
action versions in existing workflows.

### Done in current remediation batch

- Added `permissions: contents: read` to the new `mac-audit` and `shellcheck`
  workflows.
- Pinned `actions/checkout` in those workflows to the known v4 commit SHA.
- Limited `mac-audit`/`shellcheck` workflow triggers to `main` and relevant
  paths.

### Remaining work

- Pin all remaining workflow actions to full commit SHAs.
- Pin GitHub MCP Docker images to digests.
- Fix malformed `actions/upload-artifact` / `actions/download-artifact` versions
  in repository automation workflows.
- Replace unverified binary downloads with checksum/digest verification.
- Add artifact `retention-days` consistently.

### Acceptance criteria

- `actionlint .github/workflows/*.yml` passes.
- A workflow scan shows no `uses: owner/action@vN` references without a SHA
  unless explicitly documented.
- No direct `curl | bash`, `wget | tar`, or binary download executes without
  version/digest/checksum verification.

## Issue 3 — Docker and dependency reproducibility hardening

Priority: P1

### Context

Audit found broad passwordless sudo in the Dockerfile, an always-passing
healthcheck, and untracked/unpinned dependencies.

### Done in current remediation batch

- Removed broad passwordless sudo from the Docker runtime user.
- Removed `openssh-server` from the builder image.
- Fixed Docker healthcheck so missing `network-mode-manager.sh` fails.
- Added `.gitignore` exception for `copilot-demo/package-lock.json`.

### Remaining work

- Decide whether to remove the stale tracked `copilot-demo/pnpm-lock.yaml` or
  regenerate it with pnpm.
- Pin `ubuntu:24.04` images to digest.
- Add pinned Python requirements for Docker/GitHub workflow tooling.
- Replace `personal-config:latest` compose references with explicit
  `${IMAGE_TAG}` defaults.

### Acceptance criteria

- `docker build --check .` passes.
- `npm --prefix copilot-demo audit --audit-level=moderate` passes.
- Exactly one lockfile strategy exists for `copilot-demo`.

## Issue 4 — Remove hardcoded personal paths and usernames

Priority: P1

### Context

Audit found old hardcoded personal home-directory paths in scripts, templates,
docs, and archived plists.

### Done in current remediation batch

- Replaced active AdGuard script paths with `ADGUARD_LISTS_DIR` / `Path.home()`
  fallback.
- Replaced MCP template filesystem path with `~/Documents/dev/`.
- Replaced windscribe legacy script path with dynamic `SCRIPT_DIR`.
- Replaced several archive/docs/plist occurrences with `$HOME`, `$REPO_ROOT`, or
  current install paths.

### Remaining work

- Add a CI/pre-commit check blocking newly committed `/Users/<name>/` paths
  outside explicit fixture/archive allowlists.
- Review launchd plist templates and generate per-user paths at install time
  instead of committing machine-specific paths.

### Acceptance criteria

- A repo-wide grep for old personal home-directory paths only returns historical
  audit text in explicitly allowed archive reports, or returns nothing.
- Active scripts resolve paths from `$HOME`, `SCRIPT_DIR`, or repo root.

## Issue 5 — Symlink and launchd hardening

Priority: P2

### Context

Audit flagged symlink TOCTOU/ownership gaps and missing launchd hardening keys.

### Work items

- Add symlink ownership checks to config sync before trusting existing links.
- Verify symlink target after creation.
- Ensure sync functions fail on unreadable/missing critical targets instead of
  silently skipping.
- Add launchd hardening keys where compatible:
  - `StandardInputPath` = `/dev/null`
  - `ProcessType` = `Background`
  - `TimeOut`
  - `ThrottleInterval`
  - `AbandonProcessGroup`

### Acceptance criteria

- `./scripts/verify_all_configs.sh` passes.
- LaunchAgents load successfully on macOS after regeneration/install.

## Issue 6 — Maintenance safety guardrails

Priority: P2

### Context

Maintenance scripts perform cleanup, backup, and launchd checks that can modify
system state.

### Work items

- Add `--dry-run` support to destructive cleanup paths.
- Validate sourced config file ownership and permissions before `source`.
- Replace `eval` trap restoration where possible.
- Avoid unattended `sudo` prompts by using `sudo -n` checks or graceful skips.
- Add better deletion audit logs.

### Acceptance criteria

- `make test` passes.
- `make lint-errors` passes.
- Cleanup scripts can preview deletions without modifying files.

## Issue 7 — Media streaming credential handling hardening

Priority: P2

### Context

Some media scripts pass credentials via curl/rclone command-line arguments.

### Work items

- Use `umask 0077` before creating credential files.
- Prefer 1Password injection, `.netrc`, or secure config files over
  `curl -u user:pass`.
- Remove `rclone --user/--pass` command-line credentials where
  `RCLONE_USER`/`RCLONE_PASS` or config alternatives are supported.
- Validate filenames and remote names from rclone before copy/move operations.
- Validate JSON sidecar files before reading required keys.

### Acceptance criteria

- No hardcoded `curl -u "user:password"` examples remain.
- Credential files are created with mode `0600` from the moment of creation.
- Shell tests cover malformed rclone filenames and sidecar JSON.

## Issue 8 — AdGuard robustness and license attribution

Priority: P3

### Context

AdGuard scripts are stdlib-only but need stronger data validation and source
attribution.

### Work items

- Validate JSON schema before reading nested keys.
- Add source-list attribution/license documentation for Control D-derived data.
- Add domain format validation before writing consolidated lists.
- Replace broad `except Exception` catches with specific exception handling
  where feasible.

### Acceptance criteria

- AdGuard consolidation works against malformed JSON fixtures without crashing.
- Generated lists include attribution headers or repo docs clearly state source
  license assumptions.
