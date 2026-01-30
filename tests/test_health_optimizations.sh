#!/bin/bash
set -e

echo "Running optimization verification tests..."

# --- 1. Test percent_used ---
echo "Testing percent_used optimization..."

mock_df_output="Filesystem 512-blocks      Used Available Capacity iused      ifree %iused  Mounted on
/dev/disk1s1  976490576 433364424 532824632    45% 2348509 2664123160    0%   /"

original_percent_used() {
    echo "$mock_df_output" | awk 'NR==2 {print $5}' | tr -d '%'
}

optimized_percent_used() {
    echo "$mock_df_output" | awk 'NR==2 {print $5+0}'
}

res_orig=$(original_percent_used)
res_opt=$(optimized_percent_used)

if [[ "$res_orig" == "$res_opt" ]]; then
    echo "✅ percent_used match: $res_orig"
else
    echo "❌ percent_used mismatch: Orig='$res_orig', Opt='$res_opt'"
    exit 1
fi

# --- 2. Test count_clean ---
echo "Testing count_clean optimization..."

mock_wc_output="       42       "

original_count_clean() {
    echo "$mock_wc_output" | awk '{print $1}' | tr -d '\n'
}

optimized_count_clean() {
    local val="$mock_wc_output"
    echo "${val// /}"
}

res_orig=$(original_count_clean)
res_opt=$(optimized_count_clean)

if [[ "$res_orig" == "$res_opt" ]]; then
    echo "✅ count_clean match: $res_orig"
else
    echo "❌ count_clean mismatch: Orig='$res_orig', Opt='$res_opt'"
    exit 1
fi

# --- 3. Test uptime parsing ---
echo "Testing uptime optimization..."

# Case A: macOS style
mock_uptime_macos=" 15:33:04 up 2 days,  1:16,  2 users,  load averages: 1.63 1.93 2.05"
# Case B: Linux style
mock_uptime_linux=" 15:33:04 up 2 days,  1:16,  2 users,  load average: 0.23, 0.22, 0.10"

original_uptime_parse() {
    # Original logic (Note: It fails on Linux "load average", but works for macOS "load averages")
    # Using 'grep' to simulate input pipe
    echo "$1" | awk -F'load averages:' '{print $2}' | sed -E 's/^[[:space:]]+//' | sed -E 's/[[:space:]]+/ /g' | tr -d "\n"
}

optimized_uptime_parse() {
    echo "$1" | awk -F'load averages?: ' '{print $2}' | xargs
}

# Test macOS case
res_orig=$(original_uptime_parse "$mock_uptime_macos")
res_opt=$(optimized_uptime_parse "$mock_uptime_macos")

# Original: "1.63 1.93 2.05"
# Optimized: "1.63 1.93 2.05"
if [[ "$res_orig" == "$res_opt" ]]; then
    echo "✅ Uptime macOS match: $res_orig"
else
    echo "❌ Uptime macOS mismatch: Orig='$res_orig', Opt='$res_opt'"
    exit 1
fi

# Test Linux case
# Original logic fails (returns empty) because it searches for "load averages:" (plural)
# Optimized logic should return "0.23, 0.22, 0.10"
res_opt_linux=$(optimized_uptime_parse "$mock_uptime_linux")
expected_linux="0.23, 0.22, 0.10"

if [[ "$res_opt_linux" == "$expected_linux" ]]; then
    echo "✅ Uptime Linux match: $res_opt_linux"
else
    echo "❌ Uptime Linux mismatch: Expected='$expected_linux', Got='$res_opt_linux'"
    exit 1
fi

echo "All verification tests passed!"
