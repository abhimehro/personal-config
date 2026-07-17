# Windscribe static IP: Atlanta → Dallas (2026-07-16)

## Plan

- [x] Update `scripts/windscribe-connect.sh`: Dallas static default (IPv4);
      Atlanta/Peachtree non-static default when `WINDSCRIBE_IPV6=1`
- [x] Replace old static IP `82.21.151.194` → `82.23.253.53` in media scripts/docs
- [x] Update AGENTS.md / README / fish comments: IPv4=Dallas, IPv6=Atlanta
- [x] SSH: example HostName comment updated; no committed hardcoded IP
- [x] Archive audit: note historical Atlanta IP superseded
- [x] Extend `tests/test_windscribe_connect.sh` for new defaults
- [x] Run relevant tests; commit + push
- [x] Merge `origin/main`; resolve `tasks/todo.md` journal conflict
- [x] Update Windscribe media docs for Jellyfin primary (8096) vs Plex legacy
- [x] Promote Jellyfin `8096` remote forward to default path (user-enabled
      2026-07-17: Windscribe + Published Server URI)

## Security notes

- Static IP is operational config (not a secret), but still machine-identifying.
- IPv6 must not use Dallas static (IPv4-only) — default to Atlanta non-static.
- Jellyfin remote (8096) is the **default** remote path (Dallas static +
  Windscribe forward + Published Server URI `http://82.23.253.53:8096`).
  Protect with a strong admin password; Plex `32400` remains legacy.

## Live connect examples

```bash
# IPv4 / static Dallas
WINDSCRIBE_IPV6=0 ./scripts/windscribe-connect.sh privacy
# fish: env WINDSCRIBE_IPV6=0 ./scripts/windscribe-connect.sh privacy Dallas

# IPv6 Atlanta/Peachtree non-static
WINDSCRIBE_IPV6=1 ./scripts/windscribe-connect.sh privacy
# fish: env WINDSCRIBE_IPV6=1 ./scripts/windscribe-connect.sh privacy Atlanta
```

---

# Session: Bolt — sequential map in get_prs_summarize.py (#1655)

- [x] Use `run_in_bash_session` to execute a python script that will remove the unused `import concurrent.futures` and the usage of `concurrent.futures.ThreadPoolExecutor` in `scripts/get_prs_summarize.py`. The executor map will be replaced with a simple sequential `map(_fetch_task_wrapper, tasks)`.
- [x] Use `run_in_bash_session` to run `git diff scripts/get_prs_summarize.py` to visually verify the modifications.
- [x] Use `run_in_bash_session` to execute `flake8 scripts/get_prs_summarize.py` to verify the code passes linting.
- [x] Use `run_in_bash_session` to install the required testing dependencies and run the full test suite to ensure no functionality is broken by the refactoring: `sudo apt-get install -y bc && pip install pyyaml pytest && make test-all`.
- [x] Complete pre-commit steps to ensure proper testing, verification, review, and reflection are done.
- [x] Use the `submit` tool to create the PR with the requested format.

---

# Session: Snyk Secure-at-Inception project hooks (2026-07-16)

## Checklist

- [x] Vendor SAI scripts under `.cursor/hooks/snyk/`
- [x] Add wrapper + dependency-install reminder hook
- [x] Update `.cursor/hooks.json`
- [x] Write design + operator docs
- [x] Add shell smoke tests (`tests/test_cursor_snyk_hooks.sh` — 7/7)
- [x] Commit, push, open draft PR (#1629)
- [x] Refactor for CodeScene complexity gates (PR CI green)
- [x] Merge latest `origin/main`; resolve `tasks/todo.md` journal conflict

## Validation notes

- Live Snyk CLI / MCP auth unavailable in this cloud session (`SNYK_TOKEN` unset).
- `/snyk-fix` + `/snyk-batch-fix`: no remediations (no vuln table / no auth).
- docs-canvas: canvas SDK unavailable; shipped `docs/snyk-secure-at-inception.md`.
- Journal merge: took `main`'s current `tasks/todo.md` (Bolt session checklist from #1655) and appended this SAI section; did not resurrect the pre-#1655 LaunchAgents/Control D checklist that `main` replaced.
- 2026-07-16 (static IP PR): prepended Windscribe Dallas plan; kept main Bolt + SAI journals; did not resurrect Stream LA checklist.
