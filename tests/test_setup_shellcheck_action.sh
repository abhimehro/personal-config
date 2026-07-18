#!/usr/bin/env bash
# Smoke-test ShellCheck install allowlist + download used by setup-shellcheck.
set -euo pipefail

PASS=0
FAIL=0

pass() {
	echo "PASS: $1"
	PASS=$((PASS + 1))
}

fail() {
	echo "FAIL: $1"
	FAIL=$((FAIL + 1))
}

# SECURITY: Same allowlist as .github/actions/setup-shellcheck/action.yml
is_valid_shellcheck_version() {
	[[ "$1" =~ ^v[0-9]+\.[0-9]+\.[0-9]+$ ]]
}

echo "=== setup-shellcheck version allowlist ==="

if is_valid_shellcheck_version "v0.11.0"; then
	pass "accepts v0.11.0"
else
	fail "should accept v0.11.0"
fi

if is_valid_shellcheck_version "v0.10.0"; then
	pass "accepts v0.10.0"
else
	fail "should accept v0.10.0"
fi

if ! is_valid_shellcheck_version "0.11.0"; then
	pass "rejects missing v prefix"
else
	fail "should reject 0.11.0"
fi

if ! is_valid_shellcheck_version "v0.11.0;curl evil"; then
	pass "rejects injection payload"
else
	fail "should reject injection payload"
fi

if ! is_valid_shellcheck_version "../etc/passwd"; then
	pass "rejects path traversal"
else
	fail "should reject path traversal"
fi

if ! is_valid_shellcheck_version "latest"; then
	pass "rejects floating tag"
else
	fail "should reject latest"
fi

# Optional live download (skip on network failure)
SHELLCHECK_VERSION="v0.11.0"
case "$(uname -s)-$(uname -m)" in
Linux-x86_64) platform="linux.x86_64" ;;
Linux-aarch64 | Linux-arm64) platform="linux.aarch64" ;;
Darwin-x86_64) platform="darwin.x86_64" ;;
Darwin-arm64) platform="darwin.aarch64" ;;
*)
	echo "SKIP: live download (unsupported platform)"
	platform=""
	;;
esac

if [[ -n "${platform}" ]]; then
	TEST_DIR="$(mktemp -d)"
	trap 'rm -rf "${TEST_DIR}"' EXIT
	archive="shellcheck-${SHELLCHECK_VERSION}.${platform}.tar.xz"
	url="https://github.com/koalaman/shellcheck/releases/download/${SHELLCHECK_VERSION}/${archive}"
	if curl -fsSL --max-time 30 "${url}" -o "${TEST_DIR}/${archive}"; then
		tar -xJf "${TEST_DIR}/${archive}" -C "${TEST_DIR}"
		bin="${TEST_DIR}/shellcheck-${SHELLCHECK_VERSION}/shellcheck"
		if [[ -x "${bin}" ]] && "${bin}" --version >/dev/null; then
			pass "downloads and runs ShellCheck ${SHELLCHECK_VERSION} (${platform})"
		else
			fail "extracted binary missing or not runnable"
		fi
	else
		echo "SKIP: could not download ShellCheck release (network)"
	fi
fi

echo ""
echo "Passed: ${PASS}  Failed: ${FAIL}"
if [[ "${FAIL}" -gt 0 ]]; then
	exit 1
fi
exit 0
