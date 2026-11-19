#!/usr/bin/env bash
# Permanent probe for .github/gitleaks.toml.
#
# Two guarantees, proven rather than assumed:
#   1. A real-looking secret placed under docs/ MUST still fire. The narrow
#      value allowlist must never widen into a path blind spot -- a `(?i)docs/`
#      entry in the top-level [allowlist] paths was measured to suppress BOTH
#      the false positive AND a planted sentinel, so it is rejected here.
#   2. The two known false-positive captures ("prefix_scan.py" and "material")
#      MUST be suppressed.
#
# A verdict is never taken from gitleaks' exit code alone. 8.x exits 1 both when
# leaks are found and when the config fails to parse, so runs are classified from
# stderr plus the JSON report. See docs/DISK-GUARD.md Wiring rule 9.
#
# The static half runs without the binary so CI still fails if someone re-adds a
# directory-wide blind spot. The dynamic half SKIPs (exit 77) when gitleaks is
# absent; install with `brew install gitleaks`.
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
CONFIG="$REPO_ROOT/.github/gitleaks.toml"
TEST_DIR="$(mktemp -d)"
trap 'rm -rf "$TEST_DIR"' EXIT

PASS=0
FAIL=0
SENTINEL='pplx_TEST_NOT_A_REAL_KEY_sentinel'

pass() {
	printf 'PASS: %s\n' "$1"
	PASS=$((PASS + 1))
}
fail() {
	printf 'FAIL: %s\n' "$1"
	FAIL=$((FAIL + 1))
}

if [ ! -f "$CONFIG" ]; then
	printf 'FAIL: config not found at %s\n' "$CONFIG"
	exit 1
fi

# ---------------------------------------------------------------- static half

if grep -qF "'''^prefix_scan\.py\$'''" "$CONFIG"; then
	pass 'anchored value allowlist for prefix_scan.py is present'
else
	fail 'anchored value allowlist for prefix_scan.py is missing'
fi

if grep -qE '\|material\)' "$CONFIG"; then
	pass '"material" is in the prose stopword alternation'
else
	fail '"material" is missing from the prose stopword alternation'
fi

# The blind-spot guard, scoped to the top-level [allowlist] block. Only that
# block's paths and regexes are honoured by gitleaks, so a docs/ entry there
# silences every document in the repo -- measured to suppress a planted sentinel,
# not just the false positives. The [[allowlist.rules]] blocks further down are
# inert on 8.24.3 and 8.30.1 alike, so matching them here would be a false alarm.
# Comment lines are excluded so prose *about* the blind spot does not trip it.
TOP_ALLOWLIST="$(awk '/^\[allowlist\]/{f=1;next} /^\[/{f=0} f && $0 !~ /^[[:space:]]*#/' "$CONFIG")"

if [ -n "$TOP_ALLOWLIST" ]; then
	pass 'top-level [allowlist] block is present (the only allowlist gitleaks honours)'
else
	fail 'top-level [allowlist] block is absent -- gitleaks aborts with FTL "must contain at least one check"'
fi

if printf '%s\n' "$TOP_ALLOWLIST" | grep -q 'docs/'; then
	fail 'top-level [allowlist] covers docs/ -- that blinds every document to protect a few false positives'
else
	pass 'top-level [allowlist] does not cover docs/'
fi

# --------------------------------------------------------------- dynamic half

if ! command -v gitleaks >/dev/null 2>&1; then
	# Fail closed: a static failure must not be laundered into a skip.
	if [ "$FAIL" -ne 0 ]; then
		printf '\n%d passed, %d failed (gitleaks absent, static assertions only)\n' "$PASS" "$FAIL"
		exit 1
	fi
	printf 'SKIP: gitleaks binary not installed; static assertions only (%d passed)\n' "$PASS"
	exit 77
fi

REPO="$TEST_DIR/repo"
mkdir -p "$REPO/docs" "$TEST_DIR/nohooks"

# Neutralise core.hooksPath: it is set globally on this workstation, and the
# throwaway repo must not inherit LFS or case-collision hooks.
gitq() {
	git -C "$REPO" -c core.hooksPath="$TEST_DIR/nohooks" "$@"
}

gitq init -q .
gitq config user.email 'probe@example.invalid'
gitq config user.name 'gitleaks-allowlist-probe'

# The first two lines carry the exact shapes that produce false positives in
# docs/jules-proactive-analysis-2026-11.md. The third is the planted sentinel
# that must survive every allowlist entry in the config.
cat >"$REPO/docs/probe.md" <<DOC
# Probe

The helper is named secret_prefix_scan.py and it anchors its regexes.
This document discusses secret material handling in the pipeline.

\`\`\`python
password = '$SENTINEL'
\`\`\`
DOC

gitq add -A >/dev/null
gitq commit -q --no-verify -m 'gitleaks allowlist probe' >/dev/null

REPORT="$TEST_DIR/report.json"
STDERR="$TEST_DIR/stderr.txt"
set +e
gitleaks git "$REPO" -c "$CONFIG" --no-banner \
	--report-format json --report-path "$REPORT" \
	>"$TEST_DIR/stdout.txt" 2>"$STDERR"
rc=$?
set -e

# Classify before asserting: a parse failure is not a scan result.
if grep -qE 'FTL|unable to load|Failed to load config' "$STDERR"; then
	fail "gitleaks could not load $CONFIG (exit $rc); see $STDERR"
	printf '\n%d passed, %d failed\n' "$PASS" "$FAIL"
	exit 1
fi

if [ ! -s "$REPORT" ]; then
	fail "gitleaks produced no report (exit $rc); a missing report is not a clean scan"
	printf '\n%d passed, %d failed\n' "$PASS" "$FAIL"
	exit 1
fi

if grep -q "$SENTINEL" "$REPORT"; then
	pass 'planted sentinel secret under docs/ still fires'
else
	fail "planted sentinel under docs/ was suppressed -- the allowlist has a docs/ blind spot (exit $rc)"
fi

if grep -q '"prefix_scan\.py"' "$REPORT"; then
	fail 'the prefix_scan.py filename fragment is still reported as a secret'
else
	pass 'prefix_scan.py filename fragment is suppressed'
fi

if grep -q '"material"' "$REPORT"; then
	fail 'the prose word "material" is still reported as a secret'
else
	pass 'prose word "material" is suppressed'
fi

printf '\n%d passed, %d failed\n' "$PASS" "$FAIL"
[ "$FAIL" -eq 0 ] || exit 1
exit 0
