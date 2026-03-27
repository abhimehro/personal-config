#!/bin/bash
# Tests for controld-service.sh

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
source "$REPO_ROOT/scripts/lib/controld-service.sh"

test_failed=0

# Mock command dependencies
secure_mkdir() {
	mkdir -p "$1"
	chmod "$2" "$1"
}
ctrld() { echo "mock_ctrld $*"; }
pgrep() { return 1; }
pkill() { return 0; }
networksetup() { echo "mock_networksetup $*" >/dev/null; }
dscacheutil() { echo "mock_dscacheutil" >/dev/null; }
killall() { echo "mock_killall" >/dev/null; }
dig() { return 0; }

test_setup_directories() {
	local tmp_dir
	tmp_dir=$(mktemp -d)

	local c_dir="$tmp_dir/controld"
	local p_dir="$tmp_dir/profiles"
	local b_dir="$tmp_dir/backup"
	local log="$tmp_dir/controld.log"

	if ! setup_directories "$c_dir" "$p_dir" "$b_dir" "$log"; then
		echo "Fail: setup_directories returned 1"
		rm -rf "$tmp_dir"
		return 1
	fi

	if [[ ! -d $c_dir ]] || [[ ! -d $p_dir ]] || [[ ! -d $b_dir ]]; then
		echo "Fail: setup_directories did not create directories"
		rm -rf "$tmp_dir"
		return 1
	fi

	if [[ ! -f $log ]]; then
		echo "Fail: setup_directories did not create log file"
		rm -rf "$tmp_dir"
		return 1
	fi

	rm -rf "$tmp_dir"
	return 0
}

test_safe_stop() {
	local tmp_dir
	tmp_dir=$(mktemp -d)

	if ! safe_stop "$tmp_dir"; then
		echo "Fail: safe_stop returned 1"
		rm -rf "$tmp_dir"
		return 1
	fi

	rm -rf "$tmp_dir"
	return 0
}

if ! test_setup_directories; then
	echo "test_setup_directories failed"
	test_failed=1
fi
if ! test_safe_stop; then
	echo "test_safe_stop failed"
	test_failed=1
fi

if [[ $test_failed -eq 0 ]]; then
	echo "test_controld_service.sh passed!"
	true
else
	false
fi
