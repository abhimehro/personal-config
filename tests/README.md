# Tests

This directory contains automated tests and benchmarks for the scripts and configurations in this repository.

## Directory Structure

```
tests/
├── benchmarks/
│   ├── benchmark_scripts.sh   # Performance benchmarking harness (hyperfine)
│   └── baselines/             # JSON baseline results (auto-generated)
├── test_*.sh                  # Shell test scripts
└── test_*.py                  # Python test scripts
```

## Running Tests

Each test script can be run directly:

```bash
# Run an individual test
./tests/test_ssh_config.sh
./tests/test_sync_all_configs.sh
./tests/test_network_mode_manager.sh

# Run all shell tests (from repo root)
for f in tests/test_*.sh; do bash "$f"; done
```

## 🏎️ Performance Benchmarks

The `benchmarks/` subdirectory contains a benchmarking harness built on
[hyperfine](https://github.com/sharkdp/hyperfine) that measures script
execution time and stores baseline results for regression tracking.

### Setup

```bash
# Install hyperfine (one-time)
brew install hyperfine
```

### Running Benchmarks

```bash
# Run all benchmarks via Makefile (recommended)
make benchmark

# Run a specific benchmark target directly
./tests/benchmarks/benchmark_scripts.sh nm-status
./tests/benchmarks/benchmark_scripts.sh sync-all
./tests/benchmarks/benchmark_scripts.sh verify-all
./tests/benchmarks/benchmark_scripts.sh all
```

### Available Targets

| Target | Script benchmarked | Description |
|--------|--------------------|-------------|
| `nm-status` | `scripts/network-mode-manager.sh status` | Network mode status check |
| `sync-all` | `scripts/sync_all_configs.sh` | Configuration sync operations |
| `verify-all` | `scripts/verify_all_configs.sh` | Configuration verification |
| `all` | All scripts above | Run every benchmark (default via `make benchmark`) |

### Benchmark Settings

| Setting | Value | Reason |
|---------|-------|--------|
| Warmup runs | 2 | Prime filesystem and OS caches before measuring |
| Benchmark runs | 5 | Enough samples for a stable mean/stddev |
| Output format | JSON | Machine-readable; stored in `baselines/` for diffing |

### Interpreting Results

Results are written to `tests/benchmarks/baselines/<target>.json`.  Each JSON
file is produced by hyperfine and contains mean execution time, standard
deviation, min/max, and per-run timings.  Compare a new run against a saved
baseline to detect regressions before merging a change:

```bash
# Run benchmark and compare to previously-saved baseline
./tests/benchmarks/benchmark_scripts.sh nm-status
# Open baselines/nm-status.json and compare "mean" to the previous value
```

### Adding a New Benchmark

1. Add a new `case` entry in `tests/benchmarks/benchmark_scripts.sh`:

```bash
"my-script")
    benchmark_cmd "my-script" "scripts/my_script.sh"
    ;;
```

2. Include the new target in the `"all"` case so it runs with `make benchmark`.

3. Update the **Available Targets** table above.

## Writing Shell Tests

Test scripts follow these conventions:

- Use `set -euo pipefail` for strict error handling.
- Create a temp directory with `mktemp -d` and clean it up with `trap cleanup EXIT`.
- Define `pass` / `fail` helper functions for consistent output.
- Source `scripts/lib/common.sh` when you need shared helpers (`make_temp_file`,
  `is_regular_file`, etc.).

### Minimal Template

```bash
#!/bin/bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

TESTS_PASSED=0
TESTS_FAILED=0
TEMP_DIR=""

cleanup() { [[ -n "$TEMP_DIR" ]] && rm -rf "$TEMP_DIR"; }
trap cleanup EXIT
TEMP_DIR="$(mktemp -d)"

pass() { echo "[PASS] $*"; ((TESTS_PASSED++)); }
fail() { echo "[FAIL] $*"; ((TESTS_FAILED++)); }

# --- tests ---
# ...

echo ""
echo "Results: $TESTS_PASSED passed, $TESTS_FAILED failed"
[[ $TESTS_FAILED -eq 0 ]]
```
