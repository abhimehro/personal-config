#!/usr/bin/env bash
# generate-mcp-configs.sh
# -----------------------------------------------------------------------------
# Source of truth : mcp-configs/mcp-servers.template.json            (op:// refs, committed)
#                   mcp-configs/antigravity-mcp-servers.template.json (op:// refs, committed)
# Generates       : runtime configs with REAL keys for each MCP client.
#
# All generated files contain live secrets -> they are written OUTSIDE this repo
# (into each app's real config dir) and/or to gitignored *.local.json paths.
# Nothing with a real key is ever written into a git-tracked path (guarded below).
#
# Secret backends (run both for now):
#   - 1Password : `op inject`  (current source of truth, op:// refs)
#   - Proton Pass: `pass-cli inject` (parallel path; see --backend proton)
#
# Usage:
#   ./generate-mcp-configs.sh                 # all targets, 1Password backend
#   ./generate-mcp-configs.sh --backend proton
#   ./generate-mcp-configs.sh ara cursor      # only specific targets
#
# Targets: ara | cursor | windsurf | windsurf-next | raycast | antigravity | all (default)
# -----------------------------------------------------------------------------
set -euo pipefail

REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
TEMPLATE="${REPO_DIR}/mcp-configs/mcp-servers.template.json"
AG_TEMPLATE="${REPO_DIR}/mcp-configs/antigravity-mcp-servers.template.json"
BACKEND="op" # op | proton

# Raycast does NOT read ~/.config/raycast — its MCP store lives inside the
# extension's data dir. This is the real, app-read path (confirmed live).
RAYCAST_DEST="$HOME/Library/Application Support/com.raycast-x.macos/extensions/7ecf9ae7-addc-4a42-83f9-57e84211471a/servers/mcp-config.json"
# Antigravity reads ~/.gemini/antigravity/mcp_config.json, which is a symlink to:
ANTIGRAVITY_DEST="$HOME/.gemini/config/mcp_config.json"

BACKUP_DIR="$HOME/.config/mcp-backups"

# ---- parse args -------------------------------------------------------------
TARGETS=()
while [[ $# -gt 0 ]]; do
	case "$1" in
	--backend)
		BACKEND="$2"
		shift 2
		;;
	--backend=*)
		BACKEND="${1#*=}"
		shift
		;;
	ara | cursor | windsurf | windsurf-next | raycast | antigravity | all)
		TARGETS+=("$1")
		shift
		;;
	-h | --help)
		grep '^#' "$0" | sed 's/^# \{0,1\}//'
		exit 0
		;;
	*)
		echo "Unknown arg: $1" >&2
		exit 2
		;;
	esac
done
[[ ${#TARGETS[@]} -eq 0 ]] && TARGETS=("all")
[[ " ${TARGETS[*]} " == *" all "* ]] && TARGETS=(ara cursor windsurf windsurf-next raycast antigravity)

[[ -f $TEMPLATE ]] || {
	echo "Template not found: $TEMPLATE" >&2
	exit 1
}

SKIPPED=()

# ---- secret injection -------------------------------------------------------
# $1 = template file. Prints same JSON with op://|pass:// refs resolved.
inject() {
	local tmpl="$1"
	case "$BACKEND" in
	op)
		command -v op >/dev/null || {
			echo "op (1Password CLI) not found" >&2
			exit 1
		}
		op inject -i "$tmpl"
		;;
	proton)
		local PASS_CLI="pass-cli"
		command -v pass-cli >/dev/null 2>&1 || PASS_CLI="$HOME/.local/bin/pass-cli"
		"$PASS_CLI" inject -i "$tmpl"
		;;
	*)
		echo "Unknown backend: $BACKEND" >&2
		exit 1
		;;
	esac
}

# ---- format transformers ----------------------------------------------------
# $1 = wrapper: "flat" | "mcpServers"   $2 = remote-url key: "url" | "serverUrl"
TRANSFORMER="${REPO_DIR}/scripts/mcp-transform.py"
transform() {
	local wrapper="$1" urlkey="$2"
	# Clear PYTHONPATH so no sitecustomize shim prints a banner that corrupts JSON.
	local PY=/usr/bin/python3
	[[ -x $PY ]] || PY=python3
	# `env -u` unsets the vars cleanly (avoids shellcheck SC1007 on `VAR= ` idiom).
	env -u PYTHONPATH -u PYTHONSTARTUP "$PY" -S "$TRANSFORMER" "$wrapper" "$urlkey"
}

backup_file() {
	# $1 = file to back up (if it exists). Secure 0700 dir, 0600 files, out of repo.
	local dest="$1"
	[[ -f $dest ]] || return 0
	mkdir -p "$BACKUP_DIR"
	chmod 700 "$BACKUP_DIR"
	local tag
	tag="$(basename "$(dirname "$dest")")__$(basename "$dest")"
	cp "$dest" "${BACKUP_DIR}/${tag}.bak.$(date +%Y%m%d%H%M%S)"
	chmod 600 "${BACKUP_DIR}/${tag}.bak."* 2>/dev/null || true
}

# Refuse to write live secrets into a git-tracked path (dotfiles-symlink leak guard).
# Returns 0 (safe to write) or 1 (tracked -> caller must skip).
assert_not_tracked() {
	local label="$1" dest="$2" real
	real="$(/usr/bin/python3 -S -c 'import os,sys;print(os.path.realpath(sys.argv[1]))' "$dest" 2>/dev/null || echo "$dest")"
	if git -C "$(dirname "$real")" rev-parse --is-inside-work-tree >/dev/null 2>&1; then
		if git -C "$(dirname "$real")" ls-files --error-unmatch "$real" >/dev/null 2>&1; then
			echo "  ✗ ${label}: REFUSING — ${real} is git-tracked. Live secrets must not be committed." >&2
			SKIPPED+=("$label")
			return 1
		fi
	fi
	return 0
}

# Generic writer: resolves $TEMPLATE, transforms, writes 0600 to $dest.
write_config() {
	local label="$1" dest="$2" wrapper="$3" urlkey="$4" tmpl="${5:-$TEMPLATE}"
	mkdir -p "$(dirname "$dest")"
	assert_not_tracked "$label" "$dest" || return 0
	backup_file "$dest"
	inject "$tmpl" | transform "$wrapper" "$urlkey" >"$dest"
	chmod 600 "$dest"
	echo "  ✓ ${label}: ${dest}"
}

# Windsurf mirror-of-Cursor: keep the live config in the repo but GITIGNORED,
# and symlink the app's real path to it (exactly how ~/.cursor/mcp.json works).
# The committed artifact is a *.template placeholder; live keys never get tracked.
write_windsurf_symlinked() {
	local label="$1" variant="$2" # variant: windsurf | windsurf-next
	local live="${REPO_DIR}/.codeium/${variant}/mcp_config.json"
	local template_file="${REPO_DIR}/.codeium/${variant}/mcp_config.json.template"
	local app_path="$HOME/.codeium/${variant}/mcp_config.json"

	mkdir -p "${REPO_DIR}/.codeium/${variant}" "$HOME/.codeium/${variant}"

	# Ensure the repo never tracks the live file: gitignore it, commit a template.
	local gi="${REPO_DIR}/.codeium/.gitignore"
	if [[ ! -f $gi ]] || ! grep -q "mcp_config.json" "$gi" 2>/dev/null; then
		{
			echo "# Live MCP configs hold resolved secrets — never commit them."
			echo "*/mcp_config.json"
			echo "!*/mcp_config.json.template"
		} >"$gi"
	fi

	# Generate the live config (gitignored path inside repo) and a placeholder template.
	backup_file "$app_path"
	inject "$TEMPLATE" | transform mcpServers serverUrl >"$live"
	chmod 600 "$live"
	# Placeholder: op:// refs intact (safe to commit) for documentation/restore.
	transform mcpServers serverUrl <"$TEMPLATE" >"$template_file"

	# Point the app's real path at the repo's gitignored live file (symlink mirror).
	if [[ -L $app_path ]]; then
		rm -f "$app_path"
	elif [[ -e $app_path ]]; then
		# real file present — backed up above; remove so we can symlink
		rm -f "$app_path"
	fi
	ln -s "$live" "$app_path"
	echo "  ✓ ${label}: $app_path -> $live (gitignored live; template committed)"
}

echo "Generating MCP configs (backend: ${BACKEND})..."
for t in "${TARGETS[@]}"; do
	case "$t" in
	ara) write_config "Ara" "$HOME/.ara/mcp-servers.json" flat url ;;
	cursor) write_config "Cursor" "$HOME/.cursor/mcp.json" mcpServers url ;;
	windsurf) write_windsurf_symlinked "Windsurf" windsurf ;;
	windsurf-next) write_windsurf_symlinked "Windsurf Next" windsurf-next ;;
	raycast) write_config "Raycast" "$RAYCAST_DEST" mcpServers url ;;
	antigravity) write_config "Antigravity" "$ANTIGRAVITY_DEST" mcpServers url "$AG_TEMPLATE" ;;
	esac
done

echo "Done. Generated files contain LIVE secrets and are 0600, outside the repo"
echo "(or gitignored inside it for the Windsurf symlink-mirror)."
if [[ ${#SKIPPED[@]} -gt 0 ]]; then
	echo "Skipped (git-tracked, would leak): ${SKIPPED[*]}" >&2
fi
