# Design: Snyk Secure-at-Inception project hooks

Date: 2026-07-16  
Repo: `personal-config`  
Status: Implement (cloud-agent autonomy; user slash-invoked create-hook + Snyk skills)

## Problem

`personal-config` had an empty `.cursor/hooks.json`. The marketplace Snyk plugin provides Secure at Inception, but project-local hooks are version-controlled, reviewable, and sync with this IaC repo.

## Approaches considered

| Approach | Pros | Cons |
|----------|------|------|
| A. Rely on marketplace plugin only | Zero maintenance | Not in git; hash path drift; hard to audit |
| B. Vendor SAI + thin wrappers (chosen) | Auditable; works offline from marketplace cache | Periodic upstream sync needed |
| C. Full local plugin under `~/.cursor/plugins/local` | Global to user | Not shared via this repo’s sync model |

**Recommendation:** B — vendor scripts, wrap with fail-open shell launchers, add dependency-install health reminder.

## Design

### Events

1. `afterFileEdit` → track edited code/manifest lines; start background `snyk code test` when CLI present.
2. `stop` → wait for scan; if new vulns on agent-edited lines, emit `followup_message` with `/snyk-batch-fix` + table (loop_limit 3).
3. `beforeShellExecution` (matcher for package managers) → allow install, inject `agent_message` to run `snyk_package_health_check` first.

### Trust boundaries

- Hook stdin is untrusted JSON from Cursor; parse defensively.
- No secrets written to state; scan cache under `/tmp/cursor-sai-*`.
- Fail open if python3/Snyk missing (do not hard-block agent work).

### Non-goals

- Replacing CI Snyk/Trunk.
- Auto-creating PRs from hooks (batch-fix stays in-dev).
- Interactive canvas UI (SDK unavailable here; markdown docs substitute).

## Success criteria

- Hooks load from `.cursor/hooks.json` with executable scripts.
- Smoke tests pass without Snyk auth.
- Docs describe `/snyk-fix`, `/snyk-batch-fix`, and health-check flow.
