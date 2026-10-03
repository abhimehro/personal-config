#!/bin/bash
# Mole - Trap Restoration
# Restore the EXIT/INT/TERM declarations emitted by Bash's trap -p as data.
# Never execute the serialized declaration: its handler may contain shell syntax.

set -euo pipefail

# Prevent multiple sourcing
if [[ -n ${MOLE_TRAPS_LOADED-} ]]; then
	return 0
fi
readonly MOLE_TRAPS_LOADED=1

mole_restore_trap() {
	local declaration="$1"
	local signal="${declaration##* }"
	# Bash serializes signals as SIGINT/SIGTERM, but older interpreters (macOS
	# ships bash 3.2 as /bin/bash) print INT/TERM. Both spellings name the same
	# three signals, so accept either; trap treats them identically.
	case "$signal" in
	EXIT | SIGINT | INT | SIGTERM | TERM) ;;
	*) return 1 ;;
	esac

	local prefix="trap -- '" suffix="' $signal"
	[[ $declaration == "$prefix"*"$suffix" ]] || return 1
	local quoted="${declaration#"$prefix"}"
	quoted="${quoted%"$suffix"}"

	# Bash encodes each embedded single quote as '\''. Reject other unquoted
	# segments before decoding; substitutions and backslashes stay literal.
	# The replacement must come from a variable: /bin/bash 3.2 (macOS) does not
	# strip quotes from a quoted replacement string in ${var//pat/repl}.
	local escaped_quote="'\\''"
	local squote="'"
	local remainder="${quoted//"$escaped_quote"/}"
	[[ $remainder != *"'"* ]] || return 1
	local handler="${quoted//"$escaped_quote"/$squote}"
	builtin trap -- "$handler" "$signal"
}
