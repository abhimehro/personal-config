#!/bin/bash

# Accept only exact output from shopt -p for the named option; invalid state is
# deliberately ignored so it cannot alter a different shell option.
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
