#!/bin/bash
#
# Parallel test runner for tests/test_*.sh
#
# Executes all shell tests concurrently and reports a consolidated pass/fail
# summary.  Exit code is non-zero when at least one test fails.
#
# Usage:  bash tests/run_all_tests.sh
#         ./tests/run_all_tests.sh

# set -e is intentionally omitted – we capture non-zero exits from child test
# processes and must not abort early.  set -u and pipefail are safe to enable.
set -uo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
TESTS_DIR="$REPO_ROOT/tests"

# Cross-platform temp directory (macOS requires the -t flag variant)
TMP_DIR="$(mktemp -d 2>/dev/null || mktemp -d -t 'run-all-tests')"

cleanup() {
    rm -rf "$TMP_DIR"
}
trap cleanup EXIT

declare -a test_pids=()
declare -a test_names=()
declare -a failed_tests=()

echo "=========================================="
echo "Running all tests in parallel"
echo "=========================================="
echo ""

# Launch every test_*.sh in the background, redirecting output to a per-test
# log file so results can be printed sequentially after all jobs finish.
for test_file in "$TESTS_DIR"/test_*.sh; do
    # Guard against an empty directory (un-expanded glob produces a literal path)
    [ -f "$test_file" ] || continue
    name="$(basename "$test_file")"
    echo "Starting $name..."
    bash "$test_file" > "$TMP_DIR/output-$name.log" 2>&1 &
    test_pids+=($!)
    test_names+=("$name")
done

echo ""

# Wait for each background job in the original order, then report its status.
# Collecting results in order makes the summary deterministic regardless of
# which tests finish first.
for i in "${!test_pids[@]}"; do
    wait "${test_pids[$i]}"
    exit_code=$?

    if [ "$exit_code" -eq 0 ]; then
        echo "✅ ${test_names[$i]}"
    else
        echo "❌ ${test_names[$i]}"
        failed_tests+=("${test_names[$i]}")
        echo "--- Output from ${test_names[$i]} ---"
        cat "$TMP_DIR/output-${test_names[$i]}.log"
        echo "--- End of output ---"
        echo ""
    fi
done

echo ""
echo "=========================================="

total="${#test_pids[@]}"
failed="${#failed_tests[@]}"
passed=$(( total - failed ))

echo "Summary: $passed/$total tests passed"
echo "=========================================="

# Exit 1 when any test failed so CI pipelines report the correct status.
[ "$failed" -eq 0 ]
