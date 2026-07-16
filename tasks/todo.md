# Todo: Snyk Secure-at-Inception project hooks

## Design (approved under cloud-agent autonomy)

Wire version-controlled Cursor project hooks in `personal-config` that:

1. Run **Secure at Inception** (`afterFileEdit` + `stop`) via vendored Snyk Studio recipe scripts.
2. Remind agents to run **package health checks** before installing deps (`beforeShellExecution`).
3. Document `/snyk-fix`, `/snyk-batch-fix`, and health-check usage (docs-canvas outline as markdown; canvas SDK unavailable in this environment).

## Checklist

- [x] Explore context (empty `.cursor/hooks.json`, Snyk plugin already in marketplace cache)
- [x] Vendor SAI scripts under `.cursor/hooks/snyk/`
- [x] Add wrapper + dependency-install reminder hook
- [x] Update `.cursor/hooks.json`
- [x] Write design + operator docs
- [x] Add shell smoke tests
- [x] Validate hooks locally (stdin JSON)
- [ ] Commit, push, open draft PR

## Security notes

- Fail open when Snyk CLI missing/unauthenticated (follow up via MCP `snyk_code_scan`).
- No secrets in hooks; auth via `snyk auth` / `SNYK_TOKEN`.
- Dependency hook does not block installs — injects agent guidance only.

## Validation notes (this session)

- Hook smoke tests: 7/7 passed.
- `snyk_auth` / `snyk_package_health_check`: not authenticated in this environment (MCP timeout / not authenticated).
- `/snyk-fix` + `/snyk-batch-fix`: no vulnerability table / no auth — no code remediations applied.
- docs-canvas: canvas skill SDK path missing; shipped markdown operator guide instead.
