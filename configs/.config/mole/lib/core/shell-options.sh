#!/bin/bash

# Restore a shell option from prior `shopt -p` output without eval.
#
# Only nullglob and dotglob are supported. The saved string is never executed:
# restoration happens when it begins with the exact `shopt -s|-u <option>`
# command, so injected trailing content is ignored rather than interpreted.
# Unknown options and malformed or mismatched state are deliberate no-ops,
# leaving the current shell-option state unchanged.
restore_mole_shopt_state() {
	local option="$1"
	local saved_state="$2"
	case "$option" in
		nullglob | dotglob) ;;
		*) return 0 ;;
	esac
	case "$saved_state" in
		"shopt -s $option"*) shopt -s "$option" ;;
		"shopt -u $option"*) shopt -u "$option" ;;
	esac
}
