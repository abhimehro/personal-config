#!/bin/bash
#
# Strict, non-executing loader for /etc/controld/controld.env.
#
# Usage: source "scripts/lib/controld-env.sh" && load_controld_env [FILE]
#
# SECURITY:
# - Refuses symlinks.
# - Requires regular file owned by the current user or root and mode 0600.
# - Parses only a known allowlist of keys.
# - Rejects command substitution, shell metacharacters, and malformed/duplicate keys.
# - Validates resolver IDs before loading them into the shell environment.
# - Never logs raw resolver IDs.

# Source Guard
if [[ ${_CONTROLD_ENV_SH_-} == "true" ]]; then
	return
fi
_CONTROLD_ENV_SH_="true"

# Allowlist of keys that may appear in controld.env. Everything else is rejected.
__CONTROLD_ENV_ALLOWED_KEYS=(
	"CONTROLD_DIR"
	"CONTROLD_REPO"
	"CONTROLD_BOOTSTRAP_IP"
	"CTR_PROFILE_PRIVACY_ID"
	"CTR_PROFILE_GAMING_ID"
	"CTR_PROFILE_BROWSING_ID"
	"CTRLD_PRIVACY_PROFILE"
	"CTRLD_GAMING_PROFILE"
	"CTRLD_BROWSING_PROFILE"
)

# Internal: test whether a key is in the allowlist.
__controld_env_key_allowed() {
	local key="$1" allowed
	for allowed in "${__CONTROLD_ENV_ALLOWED_KEYS[@]}"; do
		if [[ $key == "$allowed" ]]; then
			return 0
		fi
	done
	return 1
}

# Internal: validate a profile/resolver ID value.
__controld_env_validate_profile_id() {
	local key="$1" value="$2"
	if command -v validate_profile_id >/dev/null 2>&1; then
		if ! validate_profile_id "$value"; then
			echo "load_controld_env: $key is not a valid resolver ID" >&2
			return 1
		fi
	else
		# Fallback regex when network-common.sh is not loaded.
		if [[ ! $value =~ ^[a-z0-9]+$ ]]; then
			echo "load_controld_env: $key is not a valid resolver ID" >&2
			return 1
		fi
	fi
	return 0
}

# Internal: validate an IPv4/IPv6 bootstrap address.
__controld_env_validate_ip() {
	local key="$1" value="$2"
	if [[ $value =~ ^([0-9]{1,3}\.){3}[0-9]{1,3}$ ]] || [[ $value =~ ^[0-9a-fA-F:]+$ ]]; then
		return 0
	fi
	echo "load_controld_env: $key is not a valid IP address" >&2
	return 1
}

# Internal: ensure a value contains only safe characters.
__controld_env_value_is_safe() {
	local value="$1"
	# Allowed: alphanumerics, underscore, slash, dot, dash, colon (for IPv6).
	# Reject anything that could be interpreted by a shell.
	if [[ $value =~ ^[A-Za-z0-9_./:-]+$ ]]; then
		return 0
	fi
	return 1
}

# Load controld.env from FILE (default /etc/controld/controld.env).
# Sets shell variables for each allowed key.  Returns 0 on success, 1 on error.
load_controld_env() {
	local env_file="${1:-${CONTROLD_DIR:-/etc/controld}/controld.env}"

	if [[ ! -e $env_file ]]; then
		# Missing env file is not an error here; callers that require a profile ID
		# will fail closed later if the value is unset.
		return 0
	fi

	if [[ -L $env_file ]]; then
		echo "load_controld_env: $env_file is a symlink (refusing to load)" >&2
		return 1
	fi

	if [[ ! -f $env_file ]]; then
		echo "load_controld_env: $env_file is not a regular file" >&2
		return 1
	fi

	if [[ ! -r $env_file ]]; then
		echo "load_controld_env: $env_file is not readable by the current user" >&2
		return 1
	fi

	local raw_mode raw_uid perm uid expected_uid="${EUID:-${UID:-0}}"
	raw_mode=$(stat -c '%a' "$env_file" 2>/dev/null || stat -f '%Lp' "$env_file" 2>/dev/null) || {
		echo "load_controld_env: cannot stat $env_file" >&2
		return 1
	}
	# macOS %Lp may return a leading file-type nibble; keep only last three octal digits.
	perm="${raw_mode: -3}"
	raw_uid=$(stat -c '%u' "$env_file" 2>/dev/null || stat -f '%u' "$env_file" 2>/dev/null) || {
		echo "load_controld_env: cannot stat $env_file" >&2
		return 1
	}
	uid="$raw_uid"

	if [[ $perm != "600" ]]; then
		echo "load_controld_env: $env_file has unsafe permissions ($perm, expected 600)" >&2
		return 1
	fi

	if [[ $uid != "$expected_uid" && $uid != "0" ]]; then
		echo "load_controld_env: $env_file is owned by uid $uid (expected $expected_uid or root)" >&2
		return 1
	fi

	local seen_keys=""
	local line key value trimmed stripped
	local line_number=0
	local rc=0

	while IFS= read -r line || [[ -n $line ]]; do
		line_number=$((line_number + 1))

		# Trim leading/trailing whitespace.
		trimmed="${line#"${line%%[![:space:]]*}"}"
		trimmed="${trimmed%"${trimmed##*[![:space:]]}"}"

		# Skip blanks and comments.
		[[ -z $trimmed ]] && continue
		[[ $trimmed == \#* ]] && continue

		# Strip optional "export " prefix.
		stripped="$trimmed"
		if [[ $stripped == export\ * ]]; then
			stripped="${stripped#export }"
		fi

		# Split on first '='.
		if [[ $stripped != *=* ]]; then
			echo "load_controld_env: $env_file:$line_number: malformed line (no '=')" >&2
			rc=1
			continue
		fi
		key="${stripped%%=*}"
		value="${stripped#*=}"

		# Trim whitespace around key/value.
		key="${key#"${key%%[![:space:]]*}"}"
		key="${key%"${key##*[![:space:]]}"}"
		value="${value#"${value%%[![:space:]]*}"}"
		value="${value%"${value##*[![:space:]]}"}"

		# Strip one matching pair of quotes.
		# bash 3.2-safe: detect quote-wrapped values with glob patterns,
		# then strip via length math (negative substring unsupported in 3.2).
		if [[ ${#value} -ge 2 && $value == \"*\" ]]; then
			value="${value:1:${#value}-2}"
		elif [[ ${#value} -ge 2 && $value == \'*\' ]]; then
			value="${value:1:${#value}-2}"
		fi

		if [[ -z $key ]]; then
			echo "load_controld_env: $env_file:$line_number: empty key" >&2
			rc=1
			continue
		fi

		if ! __controld_env_key_allowed "$key"; then
			echo "load_controld_env: $env_file:$line_number: key '$key' is not in the allowlist" >&2
			rc=1
			continue
		fi

		if [[ " $seen_keys " == *" $key "* ]]; then
			echo "load_controld_env: $env_file:$line_number: duplicate key '$key'" >&2
			rc=1
			continue
		fi
		seen_keys="$seen_keys$key "

		# Skip if the variable is already set in the current shell environment
		# (command-line env vars take precedence over the file).
		if [[ -n ${!key-} ]]; then
			continue
		fi

		# Empty value means unset; skip and let the caller fail closed if required.
		if [[ -z $value ]]; then
			continue
		fi

		if ! __controld_env_value_is_safe "$value"; then
			echo "load_controld_env: $env_file:$line_number: key '$key' contains unsafe characters" >&2
			rc=1
			continue
		fi

		# Reject shell command substitution patterns just in case.
		# shellcheck disable=SC2016
		if [[ $value == *'$('* ]] || [[ $value == *\`* ]] || [[ $value == *'${'* ]]; then
			echo "load_controld_env: $env_file:$line_number: key '$key' contains command substitution" >&2
			rc=1
			continue
		fi

		# Validate values for known sensitive keys.
		case "$key" in
		CTR_PROFILE_*_ID | CTRLD_*_PROFILE)
			if ! __controld_env_validate_profile_id "$key" "$value"; then
				rc=1
				continue
			fi
			;;
		CONTROLD_BOOTSTRAP_IP)
			if ! __controld_env_validate_ip "$key" "$value"; then
				rc=1
				continue
			fi
			;;
		esac

		# Set the variable in the current shell.
		printf -v "$key" '%s' "$value"
	done <"$env_file"

	return "$rc"
}
