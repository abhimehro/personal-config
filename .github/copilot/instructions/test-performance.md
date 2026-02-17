# Test Suite Performance Engineering Guide

## Overview
Fast tests enable rapid development cycles. This repo has shell-based tests, Python tests (pytest), and performance benchmarks. Target: full test suite under 30 seconds.

## Current Test Structure

```
tests/
├── benchmarks/
│   └── benchmark_scripts.sh          # Performance regression tests
├── test_*.sh                          # Shell script tests
├── test_*.py                          # Python tests (pytest)
└── test_network_mode_manager.sh       # Integration tests
```

## Performance Goals
- **Unit tests:** <5 seconds total
- **Integration tests:** <15 seconds total
- **Full regression suite:** <30 seconds total
- **Benchmark tests:** Separate, can be slower (informational)

## Common Performance Issues

### 1. Slow External Commands
**Problem:** Tests call real system commands that are slow

**Example:**
```bash
# SLOW: Real network call (200-500ms)
networksetup -getairportnetwork en0

# SLOW: Real DNS lookup (100-300ms)
dig +short example.com
```

**Solution:** Mock expensive operations
```bash
# tests/test_network_mode_manager.sh
networksetup() {
  # Mock implementation
  echo "Current Wi-Fi Network: TestNetwork"
}

# Export for subprocesses
export -f networksetup

# Now test runs instantly
./scripts/network-mode-manager.sh status
```

### 2. Sequential Test Execution
**Problem:** Tests run one by one, wasting CPU cores

**Solution:** Parallel execution with pytest-xdist
```bash
# Install pytest-xdist
pip install pytest-xdist

# Run tests in parallel (auto-detect cores)
pytest -n auto tests/

# Or specify number of workers
pytest -n 4 tests/
```

**Impact:** 4x speedup on 4-core machine if tests are independent

### 3. Repeated Setup/Teardown
**Problem:** Each test creates/deletes same fixtures

**Solution:** Use shared setup with unittest setUpClass/tearDownClass (or equivalent)
```python
import unittest
import tempfile
import shutil
import os


class TestWithSharedTempDir(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # Create a temporary directory once per test class instead of per test
        cls.temp_config_dir = tempfile.mkdtemp()

    @classmethod
    def tearDownClass(cls):
        # Clean up the shared directory after all tests in this class have run
        shutil.rmtree(cls.temp_config_dir)

    def test_one(self):
        # Uses the same directory created in setUpClass
        path = os.path.join(self.temp_config_dir, "file1.txt")
        with open(path, "w") as f:
            f.write("data")
        self.assertTrue(os.path.exists(path))

    def test_two(self):
        # Reuses the same directory, avoiding repeated expensive setup
        path = os.path.join(self.temp_config_dir, "file2.txt")
        with open(path, "w") as f:
            f.write("more data")
        self.assertTrue(os.path.exists(path))
```

### 4. Testing Against Real Filesystem
**Problem:** Creating files on disk is slow (I/O bound)

**Solution:** Use in-memory filesystem
```python
from io import StringIO
import sys

# Mock file operations
def test_config_parsing(monkeypatch):
    fake_file = StringIO("config=value\n")
    monkeypatch.setattr('sys.stdin', fake_file)
    # Test runs in memory
```

## Performance Measurement

### Benchmark Entire Test Suite
```bash
# Time all tests
time make test

# Or with hyperfine for accurate stats
hyperfine --warmup 1 --runs 3 'make test'
```

### Profile Individual Tests
```bash
# Pytest with duration report
pytest --durations=10 tests/

# Shell test with timing
time bash tests/test_network_mode_manager.sh
```

### Identify Slow Tests
```bash
# pytest profiling
pytest --durations=0 tests/ | sort -k2 -hr | head -20
```

Output shows slowest tests first.

## Optimization Strategies

### Strategy 1: Incremental Testing
Only run tests affected by changes:

```bash
# Get changed files
changed_files=$(git diff --name-only HEAD~1)

# Run tests for changed scripts
for file in $changed_files; do
  if [[ $file == scripts/* ]]; then
    test_file="tests/test_$(basename "$file")"
    if [ -f "$test_file" ]; then
      bash "$test_file"
    fi
  fi
done
```

**Impact:** 90% faster for single-file changes

### Strategy 2: Test Categorization
Separate fast and slow tests:

```bash
# Fast unit tests (mocked)
pytest -m "unit" tests/

# Slow integration tests (real system)
pytest -m "integration" tests/

# Run only unit tests in CI for PRs
# Run full suite before merge
```

Mark tests in Python:
```python
import pytest

@pytest.mark.unit
def test_parse_config():
    # Fast, no I/O
    pass

@pytest.mark.integration
def test_network_switch():
    # Slow, real network calls
    pass
```

### Strategy 3: Parallel Shell Tests
Run independent shell tests in parallel:

```bash
# tests/run_all_tests.sh
pids=()

# Start all tests in the background and record their PIDs
for test in tests/test_*.sh; do
  bash "$test" &          # Run in background
  pids+=("$!")            # Record PID of last background job
done

# Wait for each test and track failures
exit_code=0
for pid in "${pids[@]}"; do
  if ! wait "$pid"; then
    exit_code=1           # Remember that at least one test failed
  fi
done

exit "$exit_code"
```

### Strategy 4: Efficient Assertions
**Slow:**
```python
# Runs command for each assertion
assert get_status() == "active"
assert get_status() == "active"
assert get_status() == "active"
```

**Fast:**
```python
# Cache result
status = get_status()
assert status == "active"
assert status == "active"
assert status == "active"
```

## Real-World Example: Optimizing Network Tests

**Before:** 45 seconds
- Called real `networksetup` (20 commands × 200ms = 4s)
- Called real `dig` (10 queries × 300ms = 3s)
- Sequential execution
- Created temp files on disk

**After:** 8 seconds (5.6x faster)
1. Mocked `networksetup` and `dig` (saved 7s)
2. Parallel test execution with pytest-xdist (saved 22s)
3. In-memory temp files (saved 8s)

**Implementation:**
```python
# tests/test_network_manager.py
from unittest.mock import patch, MagicMock

@patch('subprocess.run')
def test_network_switch(mock_run):
    # Mock networksetup responses
    mock_run.return_value = MagicMock(
        returncode=0,
        stdout="Wi-Fi: On"
    )
    
    # Test runs instantly
    result = switch_network_mode("browsing")
    assert result.success
```

## Benchmarking for Performance Regression

Create dedicated benchmark tests:

```bash
# tests/benchmarks/benchmark_scripts.sh
#!/bin/bash

# Establish baseline
baseline_file="tests/benchmarks/baselines.json"

# Benchmark critical scripts
hyperfine --export-json current.json \
  --warmup 2 --runs 5 \
  'scripts/network-mode-manager.sh status'

# Compare to baseline
current_time=$(jq '.results[0].mean' current.json)
baseline_time=$(jq '.["network-mode-manager.sh"]' "$baseline_file")

# Alert if >10% slower
if (( $(echo "$current_time > $baseline_time * 1.1" | bc -l) )); then
  echo "Performance regression detected!"
  echo "Current: ${current_time}s, Baseline: ${baseline_time}s"
  exit 1
fi
```

## CI Integration

### Fast feedback loop in CI:
```yaml
# .github/workflows/tests.yml
jobs:
  quick-tests:
    runs-on: ubuntu-latest
    steps:
      - name: Run unit tests only
        run: pytest -m "unit" tests/
        
  full-tests:
    runs-on: ubuntu-latest
    needs: quick-tests
    if: github.event_name == 'push'
    steps:
      - name: Run all tests
        run: pytest tests/
```

**Strategy:** Fast unit tests block PR, full integration tests run after merge.

## When to Optimize Tests

✅ **Optimize when:**
- Test suite takes >30 seconds
- Developers skip tests due to slowness
- CI provides feedback slowly (>2 min)
- Tests don't run in parallel

❌ **Don't optimize when:**
- Already under 10 seconds
- Tests require real system state (integration tests)
- Optimization breaks test reliability

## Success Metrics

**Measure these regularly:**
```bash
# Total test/benchmark time
time make benchmark

# Per-test timing
pytest --durations=10 tests/

# Cache effectiveness (how often mocks used)
grep "mock" tests/*.py | wc -l
```

**Target metrics:**
- 95% of tests run with mocks (fast)
- 5% integration tests (real system)
- Average test <100ms
- Total suite <30s

**Key principle:** Fast tests are run tests. Optimize for speed without sacrificing coverage or reliability. Mock external dependencies aggressively.
