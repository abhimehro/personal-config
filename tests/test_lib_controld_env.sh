#!/bin/bash
#
# Unit tests for scripts/lib/controld-env.sh
# Covers: load_controld_env permissions, parsing, validation, and precedence.

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
TEST_DIR=$(mktemp -d 2>/dev/null || mktemp -d -t 'test-lib-controld-env')
trap 'rm -rf "$TEST_DIR"' EXIT

# SECURITY: isolate from host/CI secret injection (Cloud Agent / controld.env).
# load_controld_env skips keys already set in the environment (file loses).
unset CTR_PROFILE_PRIVACY_ID CTR_PROFILE_GAMING_ID CTR_PROFILE_BROWSING_ID \
	CTRLD_PRIVACY_PROFILE CTRLD_GAMING_PROFILE CTRLD_BROWSING_PROFILE \
	CONTROLD_DIR CONTROLD_REPO CONTROLD_BOOTSTRAP_IP

# shellcheck source=scripts/lib/network-common.sh
source "$REPO_ROOT/scripts/lib/network-common.sh"
# shellcheck source=scripts/lib/controld-env.sh
source "$REPO_ROOT/scripts/lib/controld-env.sh"

PASS=0
FAIL=0

_check() {
	if "$@" >/dev/null 2>&1; then
		PASS=$((PASS + 1))
	else
		FAIL=$((FAIL + 1))
		echo "FAIL: $*"
	fi
}

_check_false() {
	if ! "$@" >/dev/null 2>&1; then
		PASS=$((PASS + 1))
	else
		FAIL=$((FAIL + 1))
		echo "FAIL (expected false): $*"
	fi
}

_check_in_subshell() {
	# Run the command in a subshell so variables set by load_controld_env do not
	# leak between test cases.
	if ("$@") >/dev/null 2>&1; then
		PASS=$((PASS + 1))
	else
		FAIL=$((FAIL + 1))
		echo "FAIL: $*"
	fi
}

_check_false_in_subshell() {
	if ! ("$@") >/dev/null 2>&1; then
		PASS=$((PASS + 1))
	else
		FAIL=$((FAIL + 1))
		echo "FAIL (expected false): $*"
	fi
}

echo "=== Testing scripts/lib/controld-env.sh ==="

# --- Missing file is not an error. ---
echo ""
echo "-- missing file --"
_check_in_subshell load_controld_env "$TEST_DIR/nonexistent.env"

# --- File permissions and type checks. ---
echo ""
echo "-- permissions and file type --"

# Symlink rejected.
mkdir -p "$TEST_DIR/symlink-test"
cat >"$TEST_DIR/symlink-test/target.env" <<'EOF'
CTR_PROFILE_PRIVACY_ID=testprivacyid
EOF
chmod 600 "$TEST_DIR/symlink-test/target.env"
ln -sf "$TEST_DIR/symlink-test/target.env" "$TEST_DIR/symlink-test/controld.env"
_check_false_in_subshell load_controld_env "$TEST_DIR/symlink-test/controld.env"

# Bad permissions rejected.
cat >"$TEST_DIR/badperm.env" <<'EOF'
CTR_PROFILE_PRIVACY_ID=testprivacyid
EOF
chmod 644 "$TEST_DIR/badperm.env"
_check_false_in_subshell load_controld_env "$TEST_DIR/badperm.env"

# Regular file with mode 600 and safe values loads.
cat >"$TEST_DIR/valid.env" <<'EOF'
# Comment line
export CTR_PROFILE_PRIVACY_ID="testprivacyid"
  CTR_PROFILE_GAMING_ID='testgamingid'

CTR_PROFILE_BROWSING_ID=testbrowsingid
CONTROLD_REPO=/tmp/example-repo
CONTROLD_BOOTSTRAP_IP=76.76.2.22
EOF
chmod 600 "$TEST_DIR/valid.env"
_check load_controld_env "$TEST_DIR/valid.env"
[[ ${CTR_PROFILE_PRIVACY_ID-} == "testprivacyid" ]] || {
	echo "FAIL: CTR_PROFILE_PRIVACY_ID not loaded"
	FAIL=$((FAIL + 1))
}
[[ ${CTR_PROFILE_GAMING_ID-} == "testgamingid" ]] || {
	echo "FAIL: CTR_PROFILE_GAMING_ID not loaded"
	FAIL=$((FAIL + 1))
}
[[ ${CTR_PROFILE_BROWSING_ID-} == "testbrowsingid" ]] || {
	echo "FAIL: CTR_PROFILE_BROWSING_ID not loaded"
	FAIL=$((FAIL + 1))
}
[[ ${CONTROLD_REPO-} == "/tmp/example-repo" ]] || {
	echo "FAIL: CONTROLD_REPO not loaded"
	FAIL=$((FAIL + 1))
}
[[ ${CONTROLD_BOOTSTRAP_IP-} == "76.76.2.22" ]] || {
	echo "FAIL: CONTROLD_BOOTSTRAP_IP not loaded"
	FAIL=$((FAIL + 1))
}
unset CTR_PROFILE_PRIVACY_ID CTR_PROFILE_GAMING_ID CTR_PROFILE_BROWSING_ID CTRLD_PRIVACY_PROFILE CTRLD_GAMING_PROFILE CTRLD_BROWSING_PROFILE CONTROLD_DIR CONTROLD_REPO CONTROLD_BOOTSTRAP_IP

# --- Validation and parsing errors. ---
echo ""
echo "-- validation and parsing --"

# Unknown key rejected.
cat >"$TEST_DIR/unknown.env" <<'EOF'
UNKNOWN_KEY=value
EOF
chmod 600 "$TEST_DIR/unknown.env"
_check_false_in_subshell load_controld_env "$TEST_DIR/unknown.env"

# Duplicate key rejected.
cat >"$TEST_DIR/dup.env" <<'EOF'
CTR_PROFILE_PRIVACY_ID=testprivacyid
CTR_PROFILE_PRIVACY_ID=anotherid
EOF
chmod 600 "$TEST_DIR/dup.env"
_check_false_in_subshell load_controld_env "$TEST_DIR/dup.env"

# Malformed line rejected.
cat >"$TEST_DIR/malformed.env" <<'EOF'
CTR_PROFILE_PRIVACY_ID
EOF
chmod 600 "$TEST_DIR/malformed.env"
_check_false_in_subshell load_controld_env "$TEST_DIR/malformed.env"

# Invalid resolver ID rejected.
cat >"$TEST_DIR/invalid.env" <<'EOF'
CTR_PROFILE_PRIVACY_ID=your_privacy_id_here
EOF
chmod 600 "$TEST_DIR/invalid.env"
_check_false_in_subshell load_controld_env "$TEST_DIR/invalid.env"

# Unsafe characters / command substitution rejected.
cat >"$TEST_DIR/unsafe.env" <<'EOF'
CONTROLD_REPO=/tmp/repo; rm -rf /
EOF
chmod 600 "$TEST_DIR/unsafe.env"
_check_false_in_subshell load_controld_env "$TEST_DIR/unsafe.env"

cat >"$TEST_DIR/subst.env" <<'EOF'
CTR_PROFILE_PRIVACY_ID=$(id)
EOF
chmod 600 "$TEST_DIR/subst.env"
_check_false_in_subshell load_controld_env "$TEST_DIR/subst.env"

# Bad bootstrap IP rejected.
cat >"$TEST_DIR/badip.env" <<'EOF'
CTR_PROFILE_PRIVACY_ID=testprivacyid
CONTROLD_BOOTSTRAP_IP=not-an-ip
EOF
chmod 600 "$TEST_DIR/badip.env"
_check_false_in_subshell load_controld_env "$TEST_DIR/badip.env"

# --- Precedence: env vars win over file. ---
echo ""
echo "-- precedence --"
(
	export CTR_PROFILE_PRIVACY_ID="envoverrideid"
	load_controld_env "$TEST_DIR/valid.env"
	[[ ${CTR_PROFILE_PRIVACY_ID-} == "envoverrideid" ]] || {
		echo "FAIL: env var should override file"
		exit 1
	}
)
PASS=$((PASS + 1))

echo ""
echo "=== Results: $PASS passed, $FAIL failed ==="

if [[ $FAIL -gt 0 ]]; then
	exit 1
fi
