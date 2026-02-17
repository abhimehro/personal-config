# Maintenance System Performance Guide

## Overview
The `maintenance/` directory contains 30+ automated scripts for system cleanup, health checks, analytics, and optimization. These run via LaunchAgents on schedules (daily, weekly, monthly).

## Performance Goals
- **Fast user-triggered commands:** <1 second for status checks
- **Efficient background tasks:** Minimal CPU/disk I/O during user work
- **Smart scheduling:** Skip unnecessary work when system is idle
- **Low resource footprint:** Don't impact foreground applications

## Common Performance Issues

### 1. Redundant Filesystem Scans
Multiple maintenance scripts scan the same directories:

**Problem:**
```bash
# health_check.sh
find ~/Library/Logs -type f -mtime +30

# deep_cleaner.sh  
find ~/Library/Logs -type f -mtime +30

# analytics_dashboard.sh
find ~/Library/Logs -type f -mtime +30
```

**Solution:** Shared cache for filesystem metadata
```bash
# Shared cache in /tmp/maintenance_cache/
CACHE_DIR="/tmp/maintenance_cache"
CACHE_FILE="$CACHE_DIR/logs_inventory.txt"
CACHE_AGE_LIMIT=300  # 5 minutes

mkdir -p "$CACHE_DIR"

if [ -f "$CACHE_FILE" ]; then
  # Cross-platform stat:
  # - GNU coreutils (Linux / GitHub Actions):   stat -c %Y
  # - BSD/macOS:                               stat -f %m
  if stat --version >/dev/null 2>&1; then
    # GNU stat detected
    cache_mtime=$(stat -c %Y "$CACHE_FILE")
  else
    # Fallback for BSD/macOS stat
    cache_mtime=$(stat -f %m "$CACHE_FILE")
  fi

  if [ $(( $(date +%s) - cache_mtime )) -lt $CACHE_AGE_LIMIT ]; then
    # Use cached results
    cat "$CACHE_FILE"
  else
    # Cache too old - rebuild
    find ~/Library/Logs -type f -mtime +30 > "$CACHE_FILE"
    cat "$CACHE_FILE"
  fi
else
  # No cache yet - build it
  find ~/Library/Logs -type f -mtime +30 > "$CACHE_FILE"
  cat "$CACHE_FILE"
fi
```

### 2. Full Scans on Every Run
LaunchAgent scripts that process all files repeatedly:

**Solution:** Track last run and process incrementally
```bash
STATE_FILE="/tmp/maintenance_state/last_cleanup.txt"

if [ -f "$STATE_FILE" ]; then
  last_run=$(cat "$STATE_FILE")
  # Only process files modified since last run
  find ~/Downloads -type f -newermt "$last_run"
else
  # First run - process all
  find ~/Downloads -type f
fi

# Save current timestamp for next run
date -Iseconds > "$STATE_FILE"
```

### 3. Heavy Scripts on Tight Schedules
Some LaunchAgents run too frequently for their workload:

**Optimization checklist:**
- Is hourly really needed? Try daily first
- Can the script exit early if no work needed?
- Should it skip when battery is low?
- Should it skip when system is under load?

**Smart scheduling pattern:**
```bash
# Check if system is busy before doing expensive work
if [ "$(sysctl -n vm.loadavg | cut -d' ' -f2 | cut -d. -f1)" -gt 2 ]; then
  echo "System load high, skipping maintenance"
  exit 0
fi

# Check battery level for laptop
if pmset -g batt | grep -q 'Battery'; then
  battery_pct=$(pmset -g batt | grep -o '[0-9]\+%' | tr -d '%')
  if [ "$battery_pct" -lt 30 ]; then
    echo "Battery low, skipping maintenance"
    exit 0
  fi
fi

# Proceed with maintenance work...
```

## Performance Measurement for Maintenance Scripts

### Benchmark Individual Scripts
```bash
hyperfine --warmup 1 --runs 3 \
  'maintenance/bin/health_check.sh' \
  'maintenance/bin/deep_cleaner.sh'
```

### Profile Resource Usage
Use `time` with `-l` for detailed stats:
```bash
/usr/bin/time -l ./maintenance/bin/analytics_dashboard.sh
```

Output shows:
- Real time, user time, system time
- Maximum resident memory
- Page faults (indicates I/O bottlenecks)

### Monitor LaunchAgent Performance
Check actual CPU time from launchd:
```bash
sudo launchctl print system | grep maintenance
```

## Optimization Strategies

### Strategy 1: Batch Related Operations
Instead of running 10 small scripts hourly, combine into one script:

**Before:** 10 scripts × 0.5s startup overhead = 5s wasted
**After:** 1 script with 10 functions = 0.5s startup overhead

### Strategy 2: Parallelize Independent Tasks
For maintenance scripts with multiple independent checks:
```bash
check_logs &
check_caches &
check_downloads &
check_trash &

wait  # Wait for all background jobs
```

**Warning:** Don't parallelize if tasks compete for same resource (e.g., disk)

### Strategy 3: Use Lower-Level Commands
Some commands are faster than others:

**Slow:**
```bash
defaults read com.apple.Safari
```

**Fast:**
```bash
/usr/libexec/PlistBuddy -c "Print" ~/Library/Preferences/com.apple.Safari.plist
```

**Even faster (if just checking existence):**
```bash
[ -f ~/Library/Preferences/com.apple.Safari.plist ]
```

### Strategy 4: Limit Scope
Don't scan everything if you only need recent data:
```bash
# Slow: scan all logs
find ~/Library/Logs -type f

# Fast: only recent logs
find ~/Library/Logs -type f -mtime -7
```

## Measuring Impact on User Experience

### CPU Time Budget
LaunchAgent scripts should aim for:
- **Critical path (user waiting):** <100ms
- **Background tasks (hourly):** <1s
- **Deep maintenance (daily/weekly):** <30s

### Disk I/O Budget
Use `iostat` to measure impact:
```bash
# Start monitoring
iostat -w 1 > iostat.log &
IOSTAT_PID=$!

# Run maintenance script
./maintenance/bin/deep_cleaner.sh

# Stop monitoring
kill $IOSTAT_PID

# Check disk I/O
cat iostat.log
```

## Real-World Optimization Example

**Before:** `analytics_dashboard.sh` took 12s
- 5 separate `find` commands
- No caching
- Full recursive scans

**After:** Optimized to 2s (6x faster)
1. Shared cache for directory listings (saved 4s)
2. Combined multiple `find` with `-o` flag (saved 3s)
3. Limited depth with `-maxdepth 2` (saved 2s)
4. Early exit when no new data (saved 1s on subsequent runs)

**Measurement approach:**
```bash
# Created tests/benchmarks/benchmark_maintenance.sh
hyperfine --warmup 1 --runs 5 \
  --export-markdown results.md \
  'old/analytics_dashboard.sh' \
  'new/analytics_dashboard.sh'
```

## When to Optimize Maintenance Scripts

✅ **High priority:**
- Scripts that run hourly or more frequently
- User-triggered commands (status checks, manual cleanup)
- Scripts causing noticeable system slowdown

❌ **Low priority:**
- Scripts that run weekly or less
- Already fast (<1s)
- One-time setup scripts

**Key principle:** Optimize scripts that run often or when users are waiting. Background maintenance has looser requirements but should still be respectful of system resources.
