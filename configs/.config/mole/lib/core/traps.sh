#!/bin/bash
# Restore the EXIT/INT/TERM declarations emitted by Bash's trap -p as data.
# Never execute the serialized declaration: its handler may contain shell syntax.
mole_restore_trap() {
	local declaration="$1"
	local signal="${declaration##* }"
	case "$signal" in
	EXIT | SIGINT | INT | SIGTERM | TERM) ;;
	*) return 1 ;;
	esac
	# Bash 3.2 prints the bare signal name; Bash 4.4+ prints the SIG* form.
	case "$signal" in
	INT) signal=SIGINT ;;
	TERM) signal=SIGTERM ;;
	esac

	local prefix="trap -- '" suffix="' $signal"
	[[ $declaration == "$prefix"*"$suffix" ]] || return 1
	local quoted="${declaration#"$prefix"}"
	quoted="${quoted%"$suffix"}"

	# Bash encodes each embedded single quote as '\''. Reject other unquoted
	# segments before decoding; substitutions and backslashes stay literal.
	local escaped_quote="'\\''"
	local remainder="${quoted//"$escaped_quote"/}"
	[[ $remainder != *"'"* ]] || return 1
	local handler="${quoted//"$escaped_quote"/"'"}"
	builtin trap -- "$handler" "$signal"
}
