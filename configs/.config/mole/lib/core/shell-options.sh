#!/bin/bash

# Only nullglob and dotglob are supported. Accept their exact `shopt -p` output;
# unknown options or malformed/mismatched state are deliberate no-ops, leaving
# the current shell-option state unchanged.
restore_mole_shopt_state() {
	local option="$1"
	local saved_state="$2"
	case "$option" in
		nullglob | dotglob) ;;
		*) return 0 ;;
	esac
	case "$saved_state" in
		"shopt -s $option") shopt -s "$option" ;;
		"shopt -u $option") shopt -u "$option" ;;
	esac
}
