#!/bin/bash

# Only nullglob and dotglob are supported. Accept their exact `shopt -p` output;
# unknown options or malformed/mismatched state are deliberate no-ops, leaving
# the current shell-option state unchanged.
restore_mole_shopt_state() {
	local option="$1"
	local saved_state="$2"
	case "$option:$saved_state" in
		nullglob:"shopt -s nullglob") shopt -s nullglob ;;
		nullglob:"shopt -u nullglob") shopt -u nullglob ;;
		dotglob:"shopt -s dotglob") shopt -s dotglob ;;
		dotglob:"shopt -u dotglob") shopt -u dotglob ;;
	esac
}
