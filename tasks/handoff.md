# Handoff: ABHI-1135 — CI caching for ShellCheck and Trunk

## ELIR

### Purpose
Add reusable GitHub Actions composite actions that install pinned ShellCheck and Trunk with `actions/cache`, and wire them into every workflow that previously re-downloaded these tools on every run.

### Security
- SHA-pinned `actions/cache@55cc834…` (v6.1.0), matching existing repo pinact style.
- ShellCheck version allowlisted (`^v[0-9]+\.[0-9]+\.[0-9]+$`) before URL construction; version passed via `env`, not interpolated into shell from untrusted expressions beyond the input.
- Cache keys contain only OS/arch/version or `hashFiles('.trunk/trunk.yaml')` — no secrets.
- Trust boundary: Actions cache restores opaque binaries; we verify executability and rely on pinned release URLs / Trunk’s own tool digests.

### Failure Modes
| Failure | Consequence | Mitigation |
| --- | --- | --- |
| Cache miss | Same latency as before | Install path unchanged |
| Cache restores non-executable blob | Job fails at verify step | `chmod +x` + explicit existence check |
| Malicious `version` input | Would craft arbitrary URL | Allowlist rejects non-semver tags |
| `trunk.yaml` bump | Cache miss + `trunk install` | Expected; warm cache on next run |

### Review Checklist
- [ ] Confirm workflows reference `./.github/actions/setup-shellcheck` / `setup-trunk`
- [ ] First CI run after merge may be cache-miss (baseline); second run should show cache hits
- [ ] Bumping ShellCheck: change default `version` in setup-shellcheck (and ideally align `.trunk/trunk.yaml`)
- [ ] Bumping Trunk tools: edit `.trunk/trunk.yaml` (auto-invalidates cache key)

### Maintenance
- Keep ShellCheck default version aligned with `lint.enabled: shellcheck@…` in `.trunk/trunk.yaml` when practical.
- Do not switch back to uncached `apt-get install shellcheck` in these workflows.
- Docs: `.github/copilot/instructions/ci-performance.md`

## Files touched
- `.github/actions/setup-shellcheck/action.yml` (new)
- `.github/actions/setup-trunk/action.yml` (new)
- `.github/workflows/{code-quality,shellcheck,mac-audit,security-scan,repository-automation-daily}.yml`
- `.github/actions/daily-perf-improver/build-steps/action.yml`
- `.github/repository-automation.yml` (verify shellcheck instead of pip install shellcheck-py)
- `.github/copilot/instructions/ci-performance.md`
- `tests/test_setup_shellcheck_action.sh`
- `tasks/todo.md`, `tasks/handoff.md`
