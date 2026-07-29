#!/usr/bin/env bash
#
# Verify no verified secrets or obvious hardcoded credentials remain in the repo.
# Satisfies ABHI-964 acceptance: trufflehog --only-verified + password grep sweep.
#
# Usage: ./scripts/verify-repo-auth-hygiene.sh

set -euo pipefail

REPO_ROOT="${REPO_ROOT:-"$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"}"
cd "$REPO_ROOT"

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

log() { printf '%b\n' "${BLUE}[INFO]${NC} $*"; }
success() { printf '%b\n' "${GREEN}[OK]${NC} $*"; }
warn() { printf '%b\n' "${YELLOW}[WARN]${NC} $*"; }
error() { printf '%b\n' "${RED}[ERROR]${NC} $*" >&2; }

fail=0

resolve_trufflehog() {
	if command -v trufflehog >/dev/null 2>&1; then
		command -v trufflehog
		return 0
	fi
	if [[ -x ${TRUFFLEHOG_BIN-} ]]; then
		printf '%s\n' "$TRUFFLEHOG_BIN"
		return 0
	fi
	return 1
}

install_trufflehog_hint() {
	error "trufflehog not found. Install one of:"
	error '  curl -sSfL https://raw.githubusercontent.com/trufflesecurity/trufflehog/main/scripts/install.sh | sh -s -- -b "$HOME/.local/bin"'
	error "  trunk init && trunk run trufflehog --help"
	error "Or set TRUFFLEHOG_BIN to the trufflehog binary path."
}

run_trufflehog() {
	local hog_bin
	if ! hog_bin="$(resolve_trufflehog)"; then
		install_trufflehog_hint
		return 1
	fi

	log "Running: trufflehog filesystem . --only-verified"
	local output
	if ! output="$("$hog_bin" filesystem . --only-verified 2>&1)"; then
		error "trufflehog exited with a non-zero status"
		printf '%s\n' "$output" >&2
		return 1
	fi

	printf '%s\n' "$output"

	if echo "$output" | grep -q '"verified_secrets": 0'; then
		success "TruffleHog reported zero verified secrets"
		return 0
	fi

	if echo "$output" | grep -E '"verified_secrets": [1-9][0-9]*'; then
		error "TruffleHog reported one or more verified secrets"
		return 1
	fi

	warn "Could not parse verified_secrets count from trufflehog output; review log above"
	return 1
}

run_password_grep() {
	log "Grepping for hardcoded password assignments (excluding tests, examples, CI)"

	local pattern='(password|passwd|pwd)[[:space:]]*[=:][[:space:]]*['\''"][^'\''"$][^'\''"]{5,}['\''"]'
	local matches
	matches="$(
		grep -rIE "$pattern" \
			--exclude-dir=.git \
			--exclude-dir=.trunk \
			--exclude-dir=.github \
			--exclude-dir=tests \
			--exclude-dir=node_modules \
			--exclude='*.example' \
			--exclude='*.example.*' \
			--exclude='pnpm-lock.yaml' \
			. 2>/dev/null || true
	)"

	if [[ -z $matches ]]; then
		success "No hardcoded password literals found outside allowed paths"
		return 0
	fi

	# Allow documented anti-patterns and placeholder docs only.
	local filtered=""
	while IFS= read -r line; do
		[[ -z $line ]] && continue
		case "$line" in
		*docs/SECURITY_PATTERNS.md* | \
			*media-streaming/configs/media-credentials.example* | \
			*media-streaming/archive/scripts/start-media-server*.sh* | \
			*media-streaming/archive/scripts/start-media-server-fast.sh* | \
			*media-streaming/BACKUP_RECOVERY.md* | \
			*.agents/skills/firebase-auth-basics/*)
			continue
			;;
		esac
		filtered+="${line}"$'\n'
	done <<<"$matches"

	if [[ -z $filtered ]]; then
		success "Grep hits were only allowed placeholders or documentation examples"
		return 0
	fi

	error "Possible hardcoded password literals:"
	printf '%s' "$filtered" >&2
	return 1
}

run_curl_basic_auth_grep() {
	log "Checking media-streaming docs for curl -u with embedded passwords (not env placeholders)"

	local bad_curl
	bad_curl="$(
		grep -rE 'curl -u[[:space:]]+[^$"\n]*:[^$"\n]{3,}' media-streaming \
			--exclude-dir=archive 2>/dev/null || true
	)"

	if [[ -z $bad_curl ]]; then
		success "No curl -u examples with embedded passwords in active media-streaming docs"
		return 0
	fi

	error "Found curl -u with possible embedded credentials:"
	printf '%s\n' "$bad_curl" >&2
	return 1
}

main() {
	log "Credential verification (ABHI-964) in ${REPO_ROOT}"

	if ! run_trufflehog; then
		fail=1
	fi

	if ! run_password_grep; then
		fail=1
	fi

	if ! run_curl_basic_auth_grep; then
		fail=1
	fi

	if [[ $fail -ne 0 ]]; then
		error "Credential verification failed"
		exit 1
	fi

	success "All credential verification checks passed"
}

main "$@"
