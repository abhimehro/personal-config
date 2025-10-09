#!/bin/bash

# Simple Health Check Script
# Works without dependencies for testing

set -euo pipefail

echo "=== Simple Health Check Started: $(date) ==="

# Basic disk usage
ROOT_USE=$(df -P / | awk 'NR==2 {print $5}' | tr -d '%')
echo "Disk usage for /: ${ROOT_USE}%"

# Memory info
if command -v vm_stat >/dev/null 2>&1; then
    FREE_PAGES=$(vm_stat | awk '/Pages free:/ {print $3}' | tr -d '.' || echo "0")
    PAGE_SIZE=$(vm_stat | awk '/page size of/ {print $8}' || echo "4096")
    FREE_MB=$(( (FREE_PAGES * PAGE_SIZE) / 1024 / 1024 ))
    echo "Free memory: ${FREE_MB} MB"
fi

# System load
LOAD_AVG=$(uptime | awk -F'load averages:' '{print $2}' | tr -d ' ' || echo "unknown")
echo "System load averages: ${LOAD_AVG}"

# Check homebrew
if command -v brew >/dev/null 2>&1; then
    echo "Homebrew: Available"
    BREW_OUTDATED=$(brew outdated 2>/dev/null | wc -l | tr -d ' ')
    echo "Outdated Homebrew packages: ${BREW_OUTDATED}"
else
    echo "Homebrew: Not available"
fi

# Network connectivity
if ping -c 1 8.8.8.8 >/dev/null 2>&1; then
    echo "Network connectivity: OK"
else
    echo "Network connectivity: ISSUES DETECTED"
fi

# Software updates
SWU=$(/usr/sbin/softwareupdate -l 2>&1 || true)
if echo "$SWU" | grep -qi "No new software available"; then
    echo "Software updates: None available"
elif echo "$SWU" | grep -qi "restart.*required\|reboot.*required"; then
    echo "Software updates: RESTART REQUIRED"
else
    UPDATE_COUNT=$(echo "$SWU" | grep -c "recommended" || echo "0")
    echo "Software updates: ${UPDATE_COUNT} available"
fi

# Check launch agents
FAILED_JOBS=$(launchctl list 2>/dev/null | awk '$3 ~ /^[1-9][0-9]*$/ {print $3":"$1}' || true)
if [[ -n "${FAILED_JOBS}" ]]; then
    echo "Launch agents with non-zero exit codes: ${FAILED_JOBS}"
else
    echo "Launch agents: All running normally"
fi

echo "=== Simple Health Check Completed: $(date) ==="