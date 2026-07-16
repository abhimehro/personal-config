#!/usr/bin/env bash
# beforeShellExecution: remind agents to health-check packages before install.
# SECURITY: Does not block installs (allow). Injects agent guidance only.
# Matches common package-manager install/add commands.
set -euo pipefail

input="$(cat || true)"
command=""

if command -v python3 >/dev/null 2>&1; then
	command="$(
		printf '%s' "$input" | python3 -c '
import json, sys
try:
    data = json.load(sys.stdin)
except Exception:
    data = {}
print(data.get("command") or "")
'
	)"
elif command -v jq >/dev/null 2>&1; then
	command="$(printf '%s' "$input" | jq -r '.command // empty' 2>/dev/null || true)"
fi

# Default allow when we cannot parse input.
if [[ -z $command ]]; then
	printf '%s\n' '{"permission":"allow"}'
	exit 0
fi

# Detect dependency install / add commands (script-side filter; matcher is a first cut).
if [[ ! $command =~ (^|[[:space:];|&])(pip3?|pipx|uv|npm|pnpm|yarn|bun|cargo|go|gem|composer|poetry|bundle)([[:space:]]|$) ]]; then
	printf '%s\n' '{"permission":"allow"}'
	exit 0
fi

if [[ ! $command =~ (install|add|get) ]]; then
	printf '%s\n' '{"permission":"allow"}'
	exit 0
fi

# Skip uninstall / list / help style commands.
if [[ $command =~ (uninstall|remove|rm |outdated|list|ls |help|--help|-h) ]]; then
	printf '%s\n' '{"permission":"allow"}'
	exit 0
fi

agent_message='Before adding a dependency, run the secure-dependency-health-check skill (or Snyk MCP snyk_package_health_check) on each candidate package. Prefer Healthy overall rating, no critical/high CVEs, and an Active/Sustainable maintenance rating. Pin an exact version from latest_version. After install, consider snyk_sca_scan on the project root.'

# JSON-escape agent_message via python3 when available, fall back to jq.
if command -v python3 >/dev/null 2>&1; then
	python3 -c '
import json, sys
msg = sys.argv[1]
print(json.dumps({
    "permission": "allow",
    "agent_message": msg,
    "user_message": "Dependency install detected — agent should verify package health with Snyk before proceeding.",
}))
' "$agent_message"
	exit 0
elif command -v jq >/dev/null 2>&1; then
	jq -c -n --arg msg "$agent_message" '{
		"permission": "allow",
		"agent_message": $msg,
		"user_message": "Dependency install detected — agent should verify package health with Snyk before proceeding."
	}'
	exit 0
fi

printf '%s\n' '{"permission":"allow"}'
exit 0
