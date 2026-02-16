#!/bin/bash
#
# Shell Script Benchmarking Harness
# Uses hyperfine to measure script performance and detect regressions
#
# Usage: ./tests/benchmarks/benchmark_scripts.sh [target_script]

set -euo pipefail

# --- Configuration ---
BASELINE_DIR="tests/benchmarks/baselines"
WARMUP_RUNS=2
BENCHMARK_RUNS=5

# Colors
BLUE='\033[0;34m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

log() { echo -e "${BLUE}[INFO]${NC}" "$@"; }
success() { echo -e "${GREEN}[PASS]${NC}" "$@"; }
warn() { echo -e "${YELLOW}[WARN]${NC}" "$@"; }
error() { echo -e "${RED}[FAIL]${NC}" "$@"; }

# Check for hyperfine
if ! command -v hyperfine >/dev/null 2>&1; then
    error "hyperfine not found. Please install it to run benchmarks:"
    echo "  brew install hyperfine"
    exit 1
fi

# Ensure baseline directory exists
mkdir -p "$BASELINE_DIR"

benchmark_cmd() {
    local name="$1"
    local cmd="$2"
    local baseline_file="$BASELINE_DIR/${name}.json"

    log "Benchmarking: $name ($cmd)"
    
    # Run benchmark
    hyperfine --warmup "$WARMUP_RUNS" --runs "$BENCHMARK_RUNS" \
        --export-json "$baseline_file" \
        "$cmd"

    success "Benchmark completed. Results saved to $baseline_file"
}

# --- Targets ---

main() {
    local target="${1:-all}"

    case "$target" in
        "status"|"nm-status")
            benchmark_cmd "nm-status" "scripts/network-mode-manager.sh status"
            ;;
        "sync"|"sync-all")
            benchmark_cmd "sync-all" "scripts/sync_all_configs.sh"
            ;;
        "verify"|"verify-all")
            benchmark_cmd "verify-all" "scripts/verify_all_configs.sh"
            ;;
        "all")
            benchmark_cmd "nm-status" "scripts/network-mode-manager.sh status"
            benchmark_cmd "sync-all" "scripts/sync_all_configs.sh"
            benchmark_cmd "verify-all" "scripts/verify_all_configs.sh"
            ;;
        *)
            error "Unknown target: $target"
            echo "Available targets: nm-status, sync-all, verify-all, all"
            exit 1
            ;;
    esac
}

main "$@"
