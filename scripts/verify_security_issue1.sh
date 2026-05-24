#!/usr/bin/env bash
# Acceptance checks for ABHI-918 / security remediation issue 1.
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "${REPO_ROOT}"

failures=0

echo "==> grep: WebDAV curl examples use placeholders only"
if grep -R 'curl -u "infuse:' media-streaming 2>/dev/null | grep -v '\${MEDIA_WEBDAV_PASS}'; then
	echo "FAIL: found curl -u infuse examples without MEDIA_WEBDAV_PASS placeholder" >&2
	failures=$((failures + 1))
else
	echo "OK"
fi

echo "==> grep: no GH_TOKEN.env reads under repo-relative email-security path"
bad_gh_token_path="$(
	grep -R '../email-security-pipeline/GH_TOKEN.env' \
		--include='*.py' --include='*.sh' . 2>/dev/null \
		| grep -v 'scripts/verify_security_issue1.sh' || true
)"
if [[ -n "${bad_gh_token_path}" ]]; then
	echo "${bad_gh_token_path}" >&2
	echo "FAIL: scripts still reference ../email-security-pipeline/GH_TOKEN.env" >&2
	failures=$((failures + 1))
else
	echo "OK"
fi

echo "==> trufflehog: verified secrets scan"
TRUFFLEHOG="${TRUFFLEHOG:-}"
if [[ -z "${TRUFFLEHOG}" ]]; then
	if command -v trufflehog >/dev/null 2>&1; then
		TRUFFLEHOG="$(command -v trufflehog)"
	elif [[ -x /tmp/bin/trufflehog ]]; then
		TRUFFLEHOG=/tmp/bin/trufflehog
	fi
fi
if [[ -z "${TRUFFLEHOG}" ]]; then
	echo "SKIP: trufflehog not installed (install from https://github.com/trufflesecurity/trufflehog)" >&2
else
	if "${TRUFFLEHOG}" filesystem . --only-verified 2>&1 | tee /tmp/trufflehog-issue1.log | grep -q 'verified_secrets": 0'; then
		echo "OK"
	else
		echo "FAIL: trufflehog reported verified secrets (see log)" >&2
		failures=$((failures + 1))
	fi
fi

if [[ "${failures}" -gt 0 ]]; then
	echo "${failures} check(s) failed" >&2
	exit 1
fi
echo "All automated ABHI-918 checks passed."
