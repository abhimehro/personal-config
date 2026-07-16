#!/usr/bin/env bash
# Shared state tracking library for maintenance scripts.
# This file is sourced, not executed directly.
#
# Usage in a maintenance script:
#   SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
#   # shellcheck disable=SC1091
#   source "$SCRIPT_DIR/../lib/state.sh"
#   state_ensure_dir

# Determine the active state directory.
# Precedence: PERSONAL_CONFIG_STATE_DIR > XDG_STATE_HOME > ~/.local/state
state_dir() {
	local dir
	if [[ -n ${PERSONAL_CONFIG_STATE_DIR-} ]]; then
		dir="$PERSONAL_CONFIG_STATE_DIR"
	elif [[ -n ${XDG_STATE_HOME-} ]]; then
		dir="$XDG_STATE_HOME/personal-config"
	else
		dir="$HOME/.local/state/personal-config"
	fi
	echo "$dir"
}

# Ensure the state directory exists with restrictive permissions.
state_ensure_dir() {
	local dir
	dir="$(state_dir)"
	if [[ ! -d $dir ]]; then
		mkdir -p "$dir"
	fi
	chmod 700 "$dir"
}

# Sanitize a string so it can be used safely in a filename.
# Strips .sh, then replaces any character not in [a-zA-Z0-9_-] with _.
state_sanitize_name() {
	local raw="${1-}"
	raw="${raw%.sh}"
	local safe
	safe=$(printf '%s' "$raw" | tr -cs 'a-zA-Z0-9_-' '_' | sed 's/^_//;s/_$//')
	if [[ -z $safe ]]; then
		echo "unknown"
	else
		echo "$safe"
	fi
}

# Return the path for a given last-run marker.
state_last_run_file() {
	local name
	name="$(state_sanitize_name "$1")"
	printf '%s\n' "$(state_dir)/${name}.last_run"
}

# Return the path for a given cache file.
state_cache_file() {
	local name
	name="$(state_sanitize_name "$1")"
	printf '%s\n' "$(state_dir)/${name}.cache"
}

# Get the last-run timestamp (returns 0 if missing, empty, or non-numeric).
state_get_last_run() {
	local file
	file="$(state_last_run_file "$1")"
	if [[ -f $file ]]; then
		local ts
		ts=$(tr -d '[:space:]' <"$file" 2>/dev/null || true)
		if [[ $ts =~ ^[0-9]+$ ]]; then
			echo "$ts"
			return 0
		fi
	fi
	echo "0"
}

# Set the last-run timestamp. Defaults to now; a specific timestamp may be passed.
# DRY_RUN=1: prints what would be written but does not change state.
state_set_last_run() {
	local name="${1-}"
	local ts="${2:-$(date +%s)}"
	local file safe_name
	safe_name="$(state_sanitize_name "$name")"
	file="$(state_dir)/${safe_name}.last_run"

	if [[ ${DRY_RUN:-0} == "1" ]]; then
		echo "[DRY RUN] Would write last_run $ts to $file" >&2
		return 0
	fi

	state_ensure_dir
	local tmp
	tmp="$(mktemp "$(state_dir)/.${safe_name}.tmp.XXXXXX")"
	printf '%s\n' "$ts" >"$tmp"
	chmod 600 "$tmp"
	mv -f "$tmp" "$file"
}

# Read a cached value. Returns empty if missing.
state_get_cache() {
	local file
	file="$(state_cache_file "$1")"
	if [[ -f $file ]]; then
		cat "$file" 2>/dev/null || true
	fi
}

# Write a cached value atomically.
# DRY_RUN=1: prints what would be written but does not change state.
state_set_cache() {
	local name="${1-}"
	local value="${2-}"
	local file safe_name
	safe_name="$(state_sanitize_name "$name")"
	file="$(state_dir)/${safe_name}.cache"

	if [[ ${DRY_RUN:-0} == "1" ]]; then
		echo "[DRY RUN] Would write cache to $file" >&2
		return 0
	fi

	state_ensure_dir
	local tmp
	tmp="$(mktemp "$(state_dir)/.${safe_name}.cache.tmp.XXXXXX")"
	printf '%s\n' "$value" >"$tmp"
	chmod 600 "$tmp"
	mv -f "$tmp" "$file"
}

# Check whether a force run was requested via FORCE_RUN=1 or a --force argument.
# shellcheck disable=SC2119,SC2120
state_force_run_requested() {
	if [[ ${FORCE_RUN:-0} == "1" ]]; then
		return 0
	fi
	for arg in "$@"; do
		if [[ $arg == "--force" ]]; then
			return 0
		fi
	done
	return 1
}

# Check whether dry-run mode is enabled.
state_is_dry_run() {
	[[ ${DRY_RUN:-0} == "1" ]]
}

# Return 0 if any file under path is newer than the saved last-run timestamp.
# FORCE_RUN=1 always returns 0. Missing state or non-existent path returns 1.
# Uses find -newermt with per-file checks to avoid directory-mtime traps.
is_modified_since_last_run() {
	local path="${1-}"
	local name="${2-}"

	if [[ -z $path ]]; then
		return 1
	fi

	if state_force_run_requested; then
		return 0
	fi

	local last_run
	last_run="$(state_get_last_run "$name")"
	if [[ $last_run -le 0 ]]; then
		return 0
	fi

	if [[ ! -e $path ]]; then
		return 1
	fi

	local changed
	changed=$(find "$path" -newermt "@$last_run" -print 2>/dev/null | head -n 1) || true
	[[ -n $changed ]]
}

# Return 0 if a timestamp (seconds since epoch) is older than the given TTL.
# Returns 0 for missing (0) or non-numeric values to ensure stale/missing state is refreshed.
state_ttl_expired() {
	local last_run="${1:-0}"
	local ttl="${2:-0}"

	if [[ ! $last_run =~ ^[0-9]+$ ]] || [[ $last_run -eq 0 ]]; then
		return 0
	fi
	if [[ ! $ttl =~ ^[0-9]+$ ]] || [[ $ttl -le 0 ]]; then
		return 0
	fi

	local now
	now="$(date +%s)"
	local elapsed=$((now - last_run))
	[[ $elapsed -ge $ttl ]]
}
