#!/usr/bin/env bash
#
# Git pre-commit hook: block commits whose STAGED content contains a credential.
#
# Scans staged blobs only (`gitleaks git --staged`) - not the working tree, not
# history. Two deliberate consequences:
#   - an unstaged edit can neither hide a leak in the commit nor block it;
#   - findings already on the default branch do not fail unrelated commits.
# The whole-repo audit stays in scripts/verify-repo-auth-hygiene.sh
# (`make verify-credentials`).
#
# Output is always --redact. A hook that prints the secret it just blocked turns
# terminal scrollback and CI logs into a second disclosure channel.
#
# Bypass:  git commit --no-verify    |    SKIP_CREDENTIAL_SCAN=1 git commit
# Strict:  STRICT_CREDENTIAL_SCAN=1 fails the commit when gitleaks is missing.
#          Default is skip-with-warning because Cursor Cloud and Devin hosts do
#          not ship gitleaks, and a gate that blocks every commit there trains
#          everyone to reach for --no-verify.
# Tool errors (any non-zero exit other than "leaks found") also fail closed.
#
# Named "credential-scan", not "secrets": .gitignore line 235 ignores `*secret*`
# to keep secret-bearing files out of the repo, so a `*secret*` filename here
# would silently never be committed.

set -euo pipefail

if [ "${SKIP_CREDENTIAL_SCAN:-0}" = "1" ] || [ "${CREDENTIAL_SCAN_SKIP:-0}" = "1" ]; then
	exit 0
fi

REPO_ROOT="$(git rev-parse --show-toplevel 2>/dev/null || pwd)"
cd "${REPO_ROOT}"

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

info() { printf '%b\n' "${BLUE}[credential-scan]${NC} $*"; }
ok() { printf '%b\n' "${GREEN}[credential-scan]${NC} $*"; }
warn() { printf '%b\n' "${YELLOW}[credential-scan]${NC} $*"; }
err() { printf '%b\n' "${RED}[credential-scan]${NC} $*" >&2; }

# Nothing staged means nothing to scan. Keeps amend/no-op commit paths free.
if git diff --cached --quiet --ignore-submodules 2>/dev/null; then
	exit 0
fi

resolve_gitleaks() {
	if [ -n "${GITLEAKS_BIN:-}" ] && [ -x "${GITLEAKS_BIN}" ]; then
		printf '%s\n' "${GITLEAKS_BIN}"
		return 0
	fi
	if command -v gitleaks >/dev/null 2>&1; then
		command -v gitleaks
		return 0
	fi
	local candidate
	for candidate in "${HOME}/.local/bin/gitleaks" /opt/homebrew/bin/gitleaks /usr/local/bin/gitleaks; do
		if [ -x "${candidate}" ]; then
			printf '%s\n' "${candidate}"
			return 0
		fi
	done
	return 1
}

install_hint() {
	err "Install one of:"
	err "  brew install gitleaks"
	err '  curl -sSfL https://raw.githubusercontent.com/gitleaks/gitleaks/master/install.sh | sh'
	err "Or set GITLEAKS_BIN=/path/to/gitleaks."
}

if ! GITLEAKS="$(resolve_gitleaks)"; then
	if [ "${STRICT_CREDENTIAL_SCAN:-0}" = "1" ]; then
		err "gitleaks not found and STRICT_CREDENTIAL_SCAN=1 is set. Aborting commit."
		install_hint
		exit 1
	fi
	warn "gitleaks not found - credential scan SKIPPED (set STRICT_CREDENTIAL_SCAN=1 to fail instead)."
	warn "Whole-repo audit still available via: make verify-credentials"
	exit 0
fi

info "scanning staged changes: gitleaks git --staged --redact"
status=0
"${GITLEAKS}" git --staged --redact --no-banner --no-color "${REPO_ROOT}" || status=$?

if [ "${status}" -eq 0 ]; then
	ok "no credentials in staged changes"
	exit 0
fi

if [ "${status}" -eq 1 ]; then
	err "Credential detected in STAGED content. Commit blocked."
	err "Findings above are redacted on purpose. To see the value on your own terminal:"
	err "  gitleaks git --staged --redact=0 ${REPO_ROOT}"
	err "Fix: remove the literal, or store it in 1Password and reference it as"
	err "     op://<vault>/<item>/<field> (see docs/SECURITY_PATTERNS.md)."
	err "Already-published credential? Rotate it - deleting the commit does not un-leak it."
else
	err "gitleaks exited ${status} (tool error, not a finding). Failing closed."
	err "Re-run manually to diagnose: gitleaks git --staged ${REPO_ROOT}"
fi
err "One-off bypass: git commit --no-verify"
exit 1
