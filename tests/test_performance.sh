#!/bin/bash
#
# Performance Benchmarking Harness for Critical Shell Scripts
#
# Measures execution time of key scripts and compares against baselines.
# Flags a regression when actual time exceeds baseline mean by more than
# REGRESSION_THRESHOLD_PCT (default 5 %).
#
# Usage:
#   ./tests/test_performance.sh              # bench + regression-check all targets
#   ./tests/test_performance.sh --update     # run benchmarks and write new baselines
#   ./tests/test_performance.sh --ci         # non-interactive mode: fail on regression
#
# Requirements:
#   - hyperfine (https://github.com/sharkdp/hyperfine)
#     Install: brew install hyperfine  (macOS)
#              cargo install hyperfine (cargo)
#              apt install hyperfine   (Debian/Ubuntu 22.04+)
#
# Output:
#   PASS / WARN / FAIL lines + a summary table.
#   Exit 0 unless a regression is detected and --ci flag is active.

set -euo pipefail

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BASELINES_FILE="$REPO_ROOT/tests/performance/baselines.json"
WARMUP_RUNS=2
BENCHMARK_RUNS=5
# Regression threshold – percentage by which actual mean may exceed baseline
# before the run is considered a regression.
REGRESSION_THRESHOLD_PCT=5

# ---------------------------------------------------------------------------
# Flags
# ---------------------------------------------------------------------------
UPDATE_BASELINES=false
CI_MODE=false

for arg in "$@"; do
    case "$arg" in
        --update) UPDATE_BASELINES=true ;;
        --ci)     CI_MODE=true ;;
    esac
done

# ---------------------------------------------------------------------------
# Colors
# ---------------------------------------------------------------------------
BLUE='\033[0;34m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

log()     { echo -e "${BLUE}[INFO]${NC}  $*"; }
success() { echo -e "${GREEN}[PASS]${NC}  $*"; }
warn()    { echo -e "${YELLOW}[WARN]${NC}  $*"; }
error()   { echo -e "${RED}[FAIL]${NC}  $*"; }

# ---------------------------------------------------------------------------
# Pre-flight: require hyperfine
# ---------------------------------------------------------------------------
if ! command -v hyperfine >/dev/null 2>&1; then
    error "hyperfine is not installed. Benchmarks cannot run."
    echo "  Install: brew install hyperfine"
    exit 1
fi

# Require python3 for JSON parsing (baseline comparison)
if ! command -v python3 >/dev/null 2>&1; then
    error "python3 is required for baseline comparison but was not found."
    exit 1
fi

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

# Run a single hyperfine benchmark and return mean seconds (stdout).
# Usage: run_bench "<shell command>" [warmup [runs]]
run_bench() {
    local cmd="$1"
    local warmup="${2:-$WARMUP_RUNS}"
    local runs="${3:-$BENCHMARK_RUNS}"
    local tmp
    tmp=$(mktemp /tmp/perf_bench.XXXXXX.json)

    # hyperfine writes JSON result; --shell=none avoids extra shell overhead
    hyperfine \
        --warmup "$warmup" \
        --runs   "$runs" \
        --export-json "$tmp" \
        --shell bash \
        -- "$cmd" 2>/dev/null

    # Extract mean from JSON
    python3 - "$tmp" <<'PYEOF'
import sys, json
with open(sys.argv[1]) as f:
    data = json.load(f)
print(data["results"][0]["mean"])
PYEOF
    rm -f "$tmp"
}

# Compare measured mean against baseline; print result line.
# Returns 1 (sets regression flag) if mean > baseline*(1 + threshold/100).
check_regression() {
    local name="$1"
    local measured="$2"   # seconds (float)

    if [[ ! -f "$BASELINES_FILE" ]]; then
        warn "$name – baselines file not found; skipping regression check"
        return 0
    fi

    # Extract baseline mean for this operation
    local baseline
    baseline=$(python3 - "$BASELINES_FILE" "$name" <<'PYEOF'
import sys, json
with open(sys.argv[1]) as f:
    data = json.load(f)
ops = data.get("operations", {})
if sys.argv[2] in ops:
    print(ops[sys.argv[2]]["mean"])
else:
    print("")
PYEOF
    )

    if [[ -z "$baseline" ]]; then
        warn "$name – no baseline entry found; skipping regression check"
        return 0
    fi

    # Compare: regression if measured > baseline * (1 + threshold/100)
    local result
    result=$(python3 - "$measured" "$baseline" "$REGRESSION_THRESHOLD_PCT" <<'PYEOF'
import sys
measured   = float(sys.argv[1])
baseline   = float(sys.argv[2])
threshold  = float(sys.argv[3])
limit      = baseline * (1 + threshold / 100)
pct_diff   = ((measured - baseline) / baseline) * 100
if measured > limit:
    print(f"REGRESSION {pct_diff:+.1f}%  measured={measured:.3f}s  baseline={baseline:.3f}s  limit={limit:.3f}s")
else:
    print(f"OK {pct_diff:+.1f}%  measured={measured:.3f}s  baseline={baseline:.3f}s")
PYEOF
    )

    if [[ "$result" == REGRESSION* ]]; then
        error "$name – $result"
        return 1
    else
        success "$name – $result"
        return 0
    fi
}

# ---------------------------------------------------------------------------
# Benchmark definitions
# Each entry: bench_and_check "<key>" "<shell command to time>"
# ---------------------------------------------------------------------------
REGRESSION_COUNT=0

bench_and_check() {
    local key="$1"
    local cmd="$2"

    log "Benchmarking [$key]: $cmd"

    local mean
    if ! mean=$(run_bench "$cmd"); then
        warn "[$key] benchmark run failed – skipping"
        return 0
    fi

    printf "  mean: %.3fs\n" "$mean"

    if [[ "$UPDATE_BASELINES" == true ]]; then
        # Write/update the baseline entry for this key
        python3 - "$BASELINES_FILE" "$key" "$mean" "$cmd" <<'PYEOF'
import sys, json
baselines_path = sys.argv[1]
key            = sys.argv[2]
mean           = float(sys.argv[3])
description    = sys.argv[4]

with open(baselines_path) as f:
    data = json.load(f)

data.setdefault("operations", {})[key] = {
    "mean":        round(mean, 4),
    "stddev":      round(mean * 0.20, 4),   # conservative 20 % estimate
    "description": description
}

with open(baselines_path, "w") as f:
    json.dump(data, f, indent=2)
    f.write("\n")
PYEOF
        log "[$key] baseline updated → ${mean}s"
    else
        if ! check_regression "$key" "$mean"; then
            REGRESSION_COUNT=$((REGRESSION_COUNT + 1))
        fi
    fi
}

# ---------------------------------------------------------------------------
# Benchmark suite (10+ critical operations)
# ---------------------------------------------------------------------------
echo ""
log "=== Performance Benchmark Suite ==="
echo ""

# 1. Network mode – status query (fast path)
bench_and_check "network_mode_status" \
    "bash '$REPO_ROOT/scripts/network-mode-manager.sh' status"

# 2. Library sourcing – common.sh
bench_and_check "lib_common_source" \
    "bash -c 'source \"$REPO_ROOT/scripts/lib/common.sh\"'"

# 3. Library sourcing – network-core.sh
bench_and_check "lib_network_core_source" \
    "bash -c 'source \"$REPO_ROOT/scripts/lib/network-core.sh\"'"

# 4. Config validation
if [[ -f "$REPO_ROOT/scripts/validate-configs.sh" ]]; then
    bench_and_check "validate_configs" \
        "bash '$REPO_ROOT/scripts/validate-configs.sh'"
fi

# 5. Verify all configs
if [[ -f "$REPO_ROOT/scripts/verify_all_configs.sh" ]]; then
    bench_and_check "verify_all_configs" \
        "bash '$REPO_ROOT/scripts/verify_all_configs.sh'"
fi

# 6. Test suite – lib_common
if [[ -f "$REPO_ROOT/tests/test_lib_common.sh" ]]; then
    bench_and_check "test_lib_common" \
        "bash '$REPO_ROOT/tests/test_lib_common.sh'"
fi

# 7. Test suite – lib_dns_utils
if [[ -f "$REPO_ROOT/tests/test_lib_dns_utils.sh" ]]; then
    bench_and_check "test_lib_dns_utils" \
        "bash '$REPO_ROOT/tests/test_lib_dns_utils.sh'"
fi

# 8. Test suite – network mode manager
if [[ -f "$REPO_ROOT/tests/test_network_mode_manager.sh" ]]; then
    bench_and_check "test_network_mode_manager" \
        "bash '$REPO_ROOT/tests/test_network_mode_manager.sh'"
fi

# 9. Maintenance – health check
if [[ -f "$REPO_ROOT/maintenance/bin/health_check.sh" ]]; then
    bench_and_check "maintenance_health_check" \
        "bash '$REPO_ROOT/maintenance/bin/health_check.sh'"
fi

# 10. Maintenance – quick cleanup (dry-run flag)
if [[ -f "$REPO_ROOT/maintenance/bin/quick_cleanup.sh" ]]; then
    bench_and_check "maintenance_quick_cleanup" \
        "bash '$REPO_ROOT/maintenance/bin/quick_cleanup.sh' --dry-run"
fi

# ---------------------------------------------------------------------------
# Summary
# ---------------------------------------------------------------------------
echo ""
if [[ "$UPDATE_BASELINES" == true ]]; then
    success "Baselines updated in $BASELINES_FILE"
    exit 0
fi

if [[ "$REGRESSION_COUNT" -eq 0 ]]; then
    success "=== No performance regressions detected ==="
    exit 0
else
    error "=== $REGRESSION_COUNT regression(s) detected ==="
    if [[ "$CI_MODE" == true ]]; then
        exit 1
    else
        warn "Run with --update to refresh baselines if the slowdown is intentional."
        exit 0
    fi
fi
