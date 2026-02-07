#!/bin/bash
# Test script for scripts/network-mode-manager.sh interactive menu

# Enable TEST_MODE to skip TTY check
export TEST_MODE=1

# Mock dependencies
# EUID=1000 # Read-only, rely on current user not being root
sudo() { echo "sudo $@"; }
command() { echo "mock command"; return 0; }
clear() { echo "[CLEAR SCREEN]"; }
error() { echo "ERROR: $@"; exit 1; }

# Source the script (assuming it's modified to allow sourcing)
# We use a trick to prevent the original main from running if it's not wrapped yet
# but since we are modifying the script in the next step, this test might fail initially if run against unmodified script.
# However, the plan says "Modify scripts/network-mode-manager.sh" in this step too.

source scripts/network-mode-manager.sh

# Mock main function to intercept calls
main() {
  echo "MOCK_MAIN_CALLED: $1 ${2:-}"
}

# Function to run a test case
run_test() {
  local input="$1"
  local expected="$2"
  local desc="$3"

  echo "---------------------------------------------------"
  echo "TEST: $desc"
  echo "INPUT: '$input'"

  # Pipe input to interactive_menu and capture output
  # We use -n to avoid sending newline if read expects just 1 char
  output=$(echo -n "$input" | interactive_menu)

  # Check if mock main was called correctly
  if echo "$output" | grep -q "$expected"; then
    echo "PASS: Found expected call '$expected'"
  else
    echo "FAIL: Did not find '$expected'"
    echo "OUTPUT WAS:"
    echo "$output"
    exit 1
  fi
}

# Run tests
run_test "1" "MOCK_MAIN_CALLED: controld privacy" "Option 1: Privacy"
run_test "2" "MOCK_MAIN_CALLED: controld browsing" "Option 2: Browsing"
run_test "3" "MOCK_MAIN_CALLED: controld gaming" "Option 3: Gaming"
run_test "4" "MOCK_MAIN_CALLED: windscribe " "Option 4: Windscribe Standalone"
run_test "5" "MOCK_MAIN_CALLED: windscribe privacy" "Option 5: Windscribe + Privacy"
run_test "6" "MOCK_MAIN_CALLED: windscribe browsing" "Option 6: Windscribe + Browsing"
run_test "7" "MOCK_MAIN_CALLED: windscribe gaming" "Option 7: Windscribe + Gaming"
run_test "8" "MOCK_MAIN_CALLED: status " "Option 8: Status"
run_test "0" "Exiting..." "Option 0: Exit"

echo "---------------------------------------------------"
echo "ALL TESTS PASSED"
