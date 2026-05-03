#!/usr/bin/env bash
# lib/brew_audit.sh — audit Homebrew package sprawl
# Variables set here (BREW_OUTDATED, BREW_CASKS, BREW_ORPHANS) are consumed by
# the parent audit.sh after sourcing; shellcheck can't see cross-file usage.
# shellcheck disable=SC2034
set -euo pipefail

check_brew() {
	header "Homebrew Package Sprawl"
	if ! command -v brew &>/dev/null; then
		warn "Homebrew not found — skipping brew audit"
		BREW_ORPHANS=0
		BREW_OUTDATED=0
		BREW_CASKS=0
		return
	fi
	local outdated
	outdated=$(brew outdated --quiet 2>/dev/null | wc -l | tr -d ' ')
	if [[ $outdated -gt 20 ]]; then
		fail "$outdated outdated formulae (run: brew upgrade)"
	elif [[ $outdated -gt 5 ]]; then
		warn "$outdated outdated formulae"
	else pass "$outdated outdated formulae"; fi
	local leaves all_leaves
	leaves=$(brew leaves 2>/dev/null | wc -l | tr -d ' ')
	all_leaves=$(brew list --formula 2>/dev/null | wc -l | tr -d ' ')
	info "Installed formulae: $all_leaves  |  Top-level leaves: $leaves"
	local casks
	casks=$(brew list --cask 2>/dev/null | wc -l | tr -d ' ')
	info "Installed casks: $casks"
	if [[ $casks -gt 50 ]]; then
		warn "$casks casks — inventory review recommended, not necessarily a security issue"
	elif [[ $casks -gt 30 ]]; then
		info "$casks casks — moderate app inventory; review occasionally"
	else pass "$casks casks — within reasonable range"; fi
	info "Brew services running:"
	brew services list 2>/dev/null | grep -v "^Name" | grep "started" |
		awk '{printf "  • %s (%s)\n", $1, $2}' || true
	BREW_OUTDATED=$outdated
	BREW_CASKS=$casks
}
