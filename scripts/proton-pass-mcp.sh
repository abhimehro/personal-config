#!/usr/bin/env bash
# proton-pass-mcp.sh — launch the Proton Pass MCP server via pass-cli.
#
# Proton Pass exposes credentials to AI agents through `pass-cli` using a
# Personal Access Token (PAT) + per-access reason. This wrapper ensures an
# isolated, authenticated session before handing off to the MCP transport.
#
# The PAT itself is stored in 1Password (op://Personal/PROTON_PASS_MCP_PAT/credential)
# so it is never written to disk in plaintext. It is read at launch time only.
#
# Requirements:
#   - pass-cli installed (~/.local/bin/pass-cli)
#   - op (1Password CLI) signed in
#   - A Proton Pass agent token stored at op://Personal/PROTON_PASS_MCP_PAT/credential
set -euo pipefail

PC="${PASS_CLI:-$HOME/.local/bin/pass-cli}"
command -v "$PC" >/dev/null 2>&1 || {
	echo "pass-cli not found at $PC" >&2
	exit 1
}

# Isolated session dir so the agent session never clobbers your interactive one.
export PROTON_PASS_SESSION_DIR="${PROTON_PASS_SESSION_DIR:-$HOME/.config/proton-pass-mcp/session}"
mkdir -p "$PROTON_PASS_SESSION_DIR"
chmod 700 "$(dirname "$PROTON_PASS_SESSION_DIR")"

# Re-auth only if the session is not active.
if ! "$PC" info >/dev/null 2>&1; then
	PAT="$(op read 'op://Personal/PROTON_PASS_MCP_PAT/credential' 2>/dev/null)" || {
		echo "Could not read Proton Pass PAT from 1Password." >&2
		echo "Create an agent token:  pass-cli agent create --expiration 6m --vault Personal 'MCP Server'" >&2
		echo "then store it:          op item create ... (op://Personal/PROTON_PASS_MCP_PAT/credential)" >&2
		exit 1
	}
	PROTON_PASS_PERSONAL_ACCESS_TOKEN="$PAT" "$PC" login >/dev/null 2>&1
fi

# Hand off to whatever MCP transport pass-cli/your bridge exposes.
# pass-cli does not ship a native `mcp` subcommand yet; if/when it does,
# replace the line below with:  exec "$PC" mcp
# For now this script simply verifies access; AI clients that shell out to
# pass-cli (with PROTON_PASS_AGENT_REASON set) will use the warmed session.
exec "$PC" "$@"
