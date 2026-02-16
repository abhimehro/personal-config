# Shell Script Performance Optimization Guide

## Repository Context
This is a macOS system automation repository with 117+ shell scripts. Key scripts manage network switching (VPN/DNS), SSH configuration, media streaming servers, and maintenance automation via LaunchAgents.

## Quick Performance Measurement

### Basic Timing
Use `time` for quick measurements:
```bash
time ./scripts/network-mode-manager.sh controld browsing
```

### Accurate Benchmarking with hyperfine
For reliable comparisons (handles warm-up, multiple runs, statistics):
```bash
hyperfine --warmup 2 --runs 10 './scripts/network-mode-manager.sh controld browsing'

# Compare before/after
hyperfine --warmup 2 --runs 5 \
  'old/script.sh' \
  'new/script.sh'
```

### Profiling Shell Execution
Use `bash -x` to see every command executed:
```bash
bash -x ./script.sh 2>&1 | ts '[%H:%M:%.S]' > profile.log
```

## Common Performance Bottlenecks in This Repo

### 1. Repeated External Command Calls
**Problem:** Scripts call `networksetup`, `scutil`, `defaults`, etc. multiple times
**Impact:** Each subprocess spawn adds 10-50ms overhead

**Bad:**
```bash
if [ "$(networksetup -getairportnetwork en0 | grep 'Current Wi-Fi')" ]; then
  # Do something
fi
if [ "$(networksetup -getairportnetwork en0 | grep 'Current Wi-Fi')" ]; then
  # Do something else - calls networksetup again!
fi
```

**Good:**
```bash
wifi_status=$(networksetup -getairportnetwork en0)
if echo "$wifi_status" | grep -q 'Current Wi-Fi'; then
  # Do something
fi
if echo "$wifi_status" | grep -q 'Current Wi-Fi'; then
  # Reuses cached result
fi
```

### 2. Inefficient Filesystem Operations
**Problem:** Multiple `find` commands, recursive directory scans
**Impact:** Can take seconds on large directories

**Optimization strategies:**
- Cache `find` results if running multiple checks
- Use `fd` (faster alternative to `find`) for repeated operations
- Limit search depth with `-maxdepth`
- Skip unnecessary directories early

### 3. Subshell Spawning
**Problem:** Command substitution `$(...)` and pipelines create subshells
**Impact:** Each adds overhead; avoid in tight loops

**Bad:**
```bash
for file in $(ls *.sh); do  # Spawns subshell + ls
  result=$(wc -l "$file")   # Spawns subshell + wc
  echo "$result"
done
```

**Good:**
```bash
for file in *.sh; do        # Shell globbing, no subshell
  read -r lines _ < <(wc -l "$file")
  echo "$lines"
done
```

### 4. Network Operations Without Timeouts
**Problem:** DNS lookups, curl calls can hang indefinitely
**Impact:** Script blocks, poor user experience

**Always use timeouts:**
```bash
# DNS lookup with timeout
timeout 2 host example.com

# curl with timeout
curl --max-time 5 --connect-timeout 2 https://api.example.com
```

## Optimization Patterns for This Repo

### Pattern 1: Shared State Caching
For LaunchAgent maintenance scripts that run repeatedly:
```bash
CACHE_FILE="/tmp/last_run_state.json"
CACHE_TTL=3600  # 1 hour

if [ -f "$CACHE_FILE" ]; then
  last_run=$(jq -r .timestamp "$CACHE_FILE")
  if [ $(($(date +%s) - last_run)) -lt $CACHE_TTL ]; then
    echo "Using cached results..."
    jq -r .results "$CACHE_FILE"
    exit 0
  fi
fi

# Do expensive work...
results=$(run_expensive_operation)

# Cache for next run
jq -n --arg ts "$(date +%s)" --arg res "$results" \
  '{timestamp: $ts, results: $res}' > "$CACHE_FILE"
```

### Pattern 2: Parallel Verification Checks
When scripts verify multiple independent conditions:
```bash
# Sequential (slow)
check_dns && check_vpn && check_firewall

# Parallel (fast)
check_dns & pid1=$!
check_vpn & pid2=$!
check_firewall & pid3=$!

wait $pid1 && wait $pid2 && wait $pid3
```

### Pattern 3: Early Exit on Fast Paths
Optimize for common case:
```bash
# Check if already in target state (fast path)
if current_mode=$(nm-status) && [ "$current_mode" = "$target_mode" ]; then
  echo "Already in $target_mode mode"
  exit 0
fi

# Do expensive mode switch...
```

## Measuring Impact

### Establish Baseline
Before optimizing, measure current performance:
```bash
hyperfine --export-json baseline.json './script.sh'
```

### Verify Improvement
After changes:
```bash
hyperfine --export-json optimized.json './script.sh'

# Compare results
jq -r '.results[0].mean' baseline.json
jq -r '.results[0].mean' optimized.json
```

### Regression Testing
Add performance tests to prevent slowdowns:
```bash
# tests/test_performance.sh
baseline=2.5  # seconds
actual=$(hyperfine --warmup 1 --runs 5 './script.sh' | grep 'Time (mean)' | awk '{print $4}')

if (( $(echo "$actual > $baseline * 1.1" | bc -l) )); then
  echo "Performance regression: $actual > $baseline"
  exit 1
fi
```

## When to Optimize

✅ **Optimize:**
- User-facing scripts (network switching, SSH config)
- LaunchAgent maintenance (runs frequently)
- CI workflows (saves minutes per run)
- Scripts >200 lines (complexity issue too)

❌ **Don't optimize:**
- One-time setup scripts
- Already fast (<1 second)
- Code clarity suffers significantly

**Remember:** Measure first, optimize second. Profile to find real bottlenecks, don't guess.
