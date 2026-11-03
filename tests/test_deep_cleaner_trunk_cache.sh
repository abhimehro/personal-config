#!/usr/bin/env bash
#
# Regression test for the Trunk-cache age-only sweeps in
# maintenance/bin/deep_cleaner.sh (the block after the Mail section).
#
# Two claims are pinned, and the second exists to keep the first honest:
#
#   1. A run that reaches past the Mail section leaves the Trunk cache tree
#      untouched -- no tool binary deleted, no repo directory removed.
#   2. CONTROL ARM: the exact commands that used to run in that block DO remove
#      the same tree. Without this, a mock find that quietly never deletes, or a
#      backdated timestamp that does not actually satisfy `-atime +N`, would make
#      claim 1 pass forever and prove nothing.
#
# deep_cleaner.sh derives TRUNK_CACHE_DIR from $HOME, so the run is aimed at a
# throwaway home. The real ~/.cache/trunk is never referenced, and nothing here
# touches launchd or the monthly agent.

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SCRIPT="$REPO_ROOT/maintenance/bin/deep_cleaner.sh"

TEST_DIR=$(mktemp -d 2>/dev/null || mktemp -d -t 'test-deep-cleaner-trunk')
trap 'rm -rf "$TEST_DIR"' EXIT

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

# 2020 is far enough back to satisfy both the 30-day and the 7-day predicate.
BACKDATE=202001010000
REPO_HASHES="aaaabbbbccccddddeeeeffff00001111 bbbbccccddddeeeeffff000011112222"

# Age a tree past both retired predicates, after every write. Split by object
# kind, because the two sweeps match different things and each platform has its
# own idea of when a read counts as an access:
#
# - Files: age the ATIME only. The tool sweep is `-type f -atime +30`, so atime
#   is the honest signal. Keeping mtime at today also takes the fixture out of
#   scope of maintenance/bin/system_cleanup.sh, which runs
#   `find /tmp -type f -mtime +7 -print -delete`: run_all_tests.sh starts every
#   test at once, that reap is recursive, and it removed this test's files from a
#   sibling's temp tree on Linux CI -- 6 files gone, all 10 directories intact,
#   because it only matches `-type f`.
# - Directories: age BOTH atime and mtime, so atime is never the odd one out.
#   Measured 2026-11-03: APFS advances an atime on read only when it is already
#   older than mtime, so a file whose atime was stamped alone (2020, mtime today)
#   had its atime refreshed to today by the very walk that counted it -- which
#   silently disarmed the repos half. Linux is stricter still: its default
#   relatime refreshes on any read older than 24h, so no stamp survives a
#   sibling's recursive /tmp walk. That is why backdate_tree is also called
#   immediately before the control arm, below.
backdate_tree() {
	local root="$1"
	find "$root" -depth -type f -exec touch -a -t "$BACKDATE" {} +
	find "$root" -depth -type d -exec touch -t "$BACKDATE" {} +
}

# ---- build an isolated ~/.cache/trunk tree, backdated past both predicates ----
build_trunk_tree() {
	local root="$1"
	local hash
	mkdir -p "$root/tools/shellcheck-0.11.0/bin" "$root/tools/trunk/fmt"
	printf '#!/bin/sh\necho fake-shellcheck\n' >"$root/tools/shellcheck-0.11.0/bin/shellcheck"
	printf '#!/bin/sh\necho fake-fmt\n' >"$root/tools/trunk/fmt/fmt"
	for hash in $REPO_HASHES; do
		mkdir -p "$root/repos/$hash/git-hooks"
		printf '#!/bin/sh\necho fake-pre-push\n' >"$root/repos/$hash/git-hooks/pre-push"
		printf 'trunk-managed\n' >"$root/repos/$hash/plumbing.txt"
	done
	backdate_tree "$root"
}

# ---- mock bin ----
MOCK_BIN="$TEST_DIR/mock_bin"
mkdir -p "$MOCK_BIN"

# The -newermt probes come from maintenance/lib/state.sh and are stubbed so every
# gated section skips deterministically and quickly. Everything else is delegated
# to the real find: if a sweep is ever re-armed here, it really deletes and this
# test sees it.
cat >"$MOCK_BIN/find" <<'MOCK'
#!/bin/bash
if [[ "$*" == *"-newermt"* ]]; then
	exit 0
fi
exec /usr/bin/find "$@"
MOCK
chmod +x "$MOCK_BIN/find"

cat >"$MOCK_BIN/du" <<'MOCK'
#!/bin/bash
if [[ "${1:-}" == "-sh" ]]; then
	echo "0B"
else
	echo ""
fi
MOCK
chmod +x "$MOCK_BIN/du"

# date mock: override %-d so the test is not calendar-dependent.
cat >"$MOCK_BIN/date" <<'MOCK'
#!/bin/bash
if [[ "${1:-}" == "+%-d" ]]; then
	case "${MOCK_DAY_OF_MONTH:-}" in
	first) echo "1" ;;
	notfirst) echo "15" ;;
	*) exec /bin/date "$@" ;;
	esac
else
	exec /bin/date "$@"
fi
MOCK
chmod +x "$MOCK_BIN/date"

# Keep the monthly run from posting a real desktop notification.
cat >"$MOCK_BIN/osascript" <<'MOCK'
#!/bin/bash
exit 0
MOCK
chmod +x "$MOCK_BIN/osascript"

# ---- helpers ----
seed_state() {
	local state_dir="$1"
	local key
	mkdir -p "$state_dir"
	for key in \
		deep_cleaner_large_files \
		deep_cleaner_app_remnants \
		deep_cleaner_system_caches \
		deep_cleaner_localizations \
		deep_cleaner_duplicates \
		deep_cleaner_mobile_backups \
		deep_cleaner_vms \
		deep_cleaner_browser_profiles \
		deep_cleaner_dev_caches \
		deep_cleaner_logs \
		deep_cleaner_mail_attachments; do
		printf '%s\n' 9999999999 >"$state_dir/${key}.last_run"
	done
}

count_files() { find "$1" -type f 2>/dev/null | wc -l | tr -d ' '; }
count_dirs() { find "$1" -mindepth 1 -type d 2>/dev/null | wc -l | tr -d ' '; }

echo "=== Testing Trunk-cache containment in maintenance/bin/deep_cleaner.sh ==="

# ---------------------------------------------------------------------------
# Setup: an isolated HOME whose .cache/trunk looks exactly like a stale one.
#
# The Mail attachments directory is created on purpose. Without it MAIL_DIRS
# stays empty and macOS bash 3.2 aborts at the `any_modified "${MAIL_DIRS[@]}"`
# call before reaching the Trunk block, which is the very behaviour the sweep
# containment is meant to be verified past.
# ---------------------------------------------------------------------------
HOME_MOCK="$TEST_DIR/home"
STATE_DIR="$TEST_DIR/state"
TRUNK="$HOME_MOCK/.cache/trunk"
mkdir -p "$HOME_MOCK/Library/Logs/maintenance" \
	"$HOME_MOCK/Library/Mail/V10/MailData/Attachments"
seed_state "$STATE_DIR"
build_trunk_tree "$TRUNK"

EXPECTED_FILES=$(count_files "$TRUNK")
EXPECTED_DIRS=$(count_dirs "$TRUNK")
[[ $EXPECTED_FILES == "6" ]] || fail "fixture built the expected number of files (got $EXPECTED_FILES, want 6)"
[[ $EXPECTED_DIRS != "0" ]] || fail "fixture built directories"

# ---------------------------------------------------------------------------
# Test 1: the run completes and reaches past the Mail section
# ---------------------------------------------------------------------------
RUN_LOG="$TEST_DIR/run.log"
if MOCK_DAY_OF_MONTH=first HOME="$HOME_MOCK" PERSONAL_CONFIG_STATE_DIR="$STATE_DIR" \
	PATH="$MOCK_BIN:$PATH" bash "$SCRIPT" --force >"$RUN_LOG" 2>&1; then
	pass "script exits 0 on a forced monthly run"
else
	fail "script exited non-zero"
	tail -20 "$RUN_LOG"
fi

# Positive signal that the Trunk block itself was entered, so "nothing was
# removed" cannot be an artefact of the block never running.
if grep -q "containment policy" "$RUN_LOG"; then
	pass "Trunk cache block was reached and reports containment"
else
	fail "no containment marker: either the block was skipped or a sweep was re-armed"
	tail -20 "$RUN_LOG"
fi

# A report file is only written at the end of the script, so its presence proves
# execution passed line 389 all the way through.
if compgen -G "$HOME_MOCK/Library/Logs/maintenance/deep_clean_report-*.txt" >/dev/null 2>&1; then
	pass "run reached the end and wrote a deep clean report"
else
	fail "no deep clean report, so execution stopped before the Trunk block"
fi

# ---------------------------------------------------------------------------
# Test 2: nothing under the Trunk cache was removed
# ---------------------------------------------------------------------------
if [[ -d "$TRUNK/repos" && -d "$TRUNK/tools" ]]; then
	pass "repos/ and tools/ roots still exist"
else
	fail "a Trunk cache root was removed"
fi

# A missing file has two possible causes, and the run log separates them: the
# containment marker above is emitted from inside the same block, so a marker
# plus lost files means something outside this script removed them.
if [[ $(count_files "$TRUNK") == "$EXPECTED_FILES" ]]; then
	pass "file count under the Trunk cache unchanged ($EXPECTED_FILES)"
else
	fail "file count under the Trunk cache changed: was $EXPECTED_FILES, now $(count_files "$TRUNK") (re-armed sweep, or an external cleaner -- see backdate_tree above)"
fi

if [[ $(count_dirs "$TRUNK") == "$EXPECTED_DIRS" ]]; then
	pass "directory count under the Trunk cache unchanged ($EXPECTED_DIRS)"
else
	fail "directory count under the Trunk cache changed: was $EXPECTED_DIRS, now $(count_dirs "$TRUNK")"
fi

for hash in $REPO_HASHES; do
	if [[ -f "$TRUNK/repos/$hash/git-hooks/pre-push" ]]; then
		pass "git-hooks/pre-push survived for repo $hash"
	else
		fail "git-hooks/pre-push was deleted for repo $hash"
	fi
done

# ---------------------------------------------------------------------------
# Test 3 (CONTROL): the two retired commands really do delete, so Test 2 has
# teeth. Run against a separate identical tree; nothing here touches the tree
# asserted above.
# ---------------------------------------------------------------------------
CONTROL="$TEST_DIR/control"
build_trunk_tree "$CONTROL"

# Re-stamp immediately before the predicates run. A backdated tree is only stale
# until something reads it: on Linux the default relatime refreshes an atime on
# the first readdir once it is past 24h, so a sibling test's recursive /tmp walk
# (system_cleanup.sh's reap) can refresh these directories between building and
# sweeping, and the control then reports "toothless" for a fixture problem
# rather than a real one. Stamping last makes the control's precondition true by
# construction on every platform.
backdate_tree "$CONTROL"

# Retired exactly as they were, including the swallowed stderr and exit status.
find "$CONTROL/tools" -type f -atime +30 -delete 2>/dev/null || true
find "$CONTROL/repos" -type d -atime +7 -exec rm -rf {} \; 2>/dev/null || true

if [[ $(count_files "$CONTROL/tools") == "0" ]]; then
	pass "control: -atime +30 -delete does remove backdated tool files"
else
	fail "control arm is toothless: tool sweep removed nothing, so Test 2 proves nothing"
fi

if [[ ! -f "$CONTROL/repos/aaaabbbbccccddddeeeeffff00001111/git-hooks/pre-push" ]]; then
	pass "control: -atime +7 -exec rm -rf does remove the repo hook directories"
else
	fail "control arm is toothless: repo sweep removed nothing, so Test 2 proves nothing"
fi

# ---------------------------------------------------------------------------
# Summary
# ---------------------------------------------------------------------------
echo ""
echo "=== Results: $PASS passed, $FAIL failed ==="
[[ $FAIL -eq 0 ]]
