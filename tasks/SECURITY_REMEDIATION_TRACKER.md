# Security Remediation Master Tracker (ABHI-950)

**Linear:**
[ABHI-950](https://linear.app/abhis-space/issue/ABHI-950/security-remediation-master-tracker)\
**Project:** Security Remediation Sprint\
**Last updated:** 2026-05-24\
**Source plan:**
[`tasks/security-remediation-plan-2026-05-01.md`](security-remediation-plan-2026-05-01.md)

This document is the repo-local status board for cross-cutting security work.
Sub-issues in Linear should link here; update checkboxes when evidence lands on
`main`.

## Theme status

| Theme                           | CWE / class | Repo scope        | Status               | Evidence                                                                                                      |
| ------------------------------- | ----------- | ----------------- | -------------------- | ------------------------------------------------------------------------------------------------------------- |
| GitHub Actions script injection | CWE-94      | `personal-config` | **Mitigated**        | `copilot-setup-steps.yml` binds `workflow_dispatch` input via `REQUEST` env; Gemini workflows use env binding |
| Spreadsheet formula injection   | CWE-1236    | `personal-config` | **Mitigated**        | `spreadsheet_safety.escape_spreadsheet_formula()` used by `scratch_inventory.py`                              |
| Command injection (shell)       | CWE-78      | `personal-config` | **Mostly mitigated** | PR automation uses argv lists (`tests/test_vulnerability_fix.py`); mole/maintenance eval hardening ongoing    |
| Supply-chain (unpinned actions) | —           | `personal-config` | **In progress**      | Many workflows ratcheted; `copilot-setup-steps.yml` pinned in this batch                                      |
| Credential exposure             | CWE-214     | `personal-config` | **In progress**      | WebDAV examples use env placeholders; rotation is manual (P0)                                                 |

## P0–P3 checklist (personal-config)

### P0 — Rotate live credentials (manual)

- [x] Remove committed WebDAV password examples (`${MEDIA_WEBDAV_PASS}`
      placeholders)
- [ ] Rotate/revoke exposed GitHub PAT (local `GH_TOKEN.env`, not tracked)
- [ ] Rotate WebDAV password in 1Password / media-server config
- [ ] Decide whether git history purge is required for old WebDAV secret

**Verify:** `trufflehog filesystem . --only-verified` reports no verified
secrets.

### P1 — GitHub Actions supply chain

- [x] `permissions: contents: read` on mac-audit / shellcheck workflows
- [x] Pin `actions/checkout` on key workflows
- [x] Pin `actions/setup-python` + `actions/github-script` on
      `copilot-setup-steps.yml` (2026-05-24)
- [ ] Pin remaining `uses: owner/action@vN` references repo-wide (see
      `rg 'uses:.*@v[0-9]' .github/workflows`)
- [ ] Pin MCP Docker images to digests
- [ ] Fix malformed artifact action versions in automation workflows
- [ ] Add consistent `retention-days` on artifacts

**Verify:** `actionlint .github/workflows/*.yml` passes.

### P1 — Docker / dependency reproducibility

- [x] Remove broad passwordless sudo from Dockerfile
- [x] Healthcheck fails when `network-mode-manager.sh` missing
- [ ] Pin `ubuntu:24.04` to digest
- [ ] Resolve `copilot-demo` single lockfile strategy (npm vs pnpm)

### P1 — Hardcoded personal paths

- [x] Replace active AdGuard / MCP / windscribe hardcoded paths
- [ ] CI guard blocking new `/Users/<name>/` outside allowlisted archives

### P2 — Symlink / launchd hardening

- [ ] Symlink ownership checks in config sync
- [ ] Post-create symlink verification
- [ ] LaunchAgent hardening keys (`StandardInputPath`, `ProcessType`, etc.)

### P2 — Maintenance safety

- [ ] `--dry-run` on destructive cleanup paths
- [ ] Validate sourced config ownership before `source`
- [ ] Replace `eval` trap restoration where feasible (`smart_scheduler.sh`,
      `performance_optimizer.sh`)

### P2 — Media credential handling

- [x] No hardcoded `curl -u user:pass` in docs
- [ ] `umask 0077` before credential file creation (audit media scripts)
- [ ] Prefer env / 1Password over CLI credential flags for rclone

### P3 — AdGuard robustness

- [ ] JSON schema validation before nested key access
- [ ] Source-list license attribution in generated lists

## Cross-repo items (tracked in Linear, implemented elsewhere)

| Item                                 | Repo                      | Notes                                           |
| ------------------------------------ | ------------------------- | ----------------------------------------------- |
| CWE-94 `workflow_dispatch` hardening | `email-security-pipeline` | See PR #881 in session notes                    |
| Broader Sentinel automation          | multiple                  | Salvage branches under `cursor-agent/salvage-*` |

## Verification commands (this repo)

```bash
make test-quick
make lint-errors
python3 -m unittest tests.test_spreadsheet_safety tests.test_vulnerability_fix tests.test_scratch_inventory
rg 'uses:.*@v[0-9]' .github/workflows --glob '*.yml' | rg -v 'ratchet:|# v'
```

## Change log

| Date       | Change                                                            | PR / commit                                     |
| ---------- | ----------------------------------------------------------------- | ----------------------------------------------- |
| 2026-05-01 | Initial remediation plan                                          | `tasks/security-remediation-plan-2026-05-01.md` |
| 2026-05-19 | CWE-94 fix in `copilot-setup-steps.yml`                           | #980                                            |
| 2026-05-24 | Master tracker + formula injection + pin copilot workflow actions | (this batch)                                    |
