# Control D DNS Switching Outage - Root Cause Analysis

## Executive Summary

**Incident Date:** September 11, 2025, 07:19:21 - 07:24:05 CDT
**Duration:** ~5 minutes of complete DNS failure, followed by manual recovery requiring system/network restarts
**Impact:** Complete internet connectivity loss on both ethernet and Wi-Fi

## Root Cause

**Primary Issue:** Port conflict and mismatch between system DNS configuration and ctrld listener
- System DNS was configured to use `*********:53`
- ctrld was **NOT** bound to port 53 (confirmed by health check: `❌ ctrld is NOT bound to port 53`)
- Windscribe VPN application was occupying port 53, preventing ctrld from binding

**Secondary Issues:**
1. **Windscribe Port Conflict**: PID 14640 (/Applications/Windscribe.app/Contents/MacOS/Windscribe) was listening on port 53
2. **Network Connectivity Issues**: ctrld couldn't reach Control D servers (I/O timeouts to `*****.controld.com`)
3. **Race Conditions**: Multiple rapid script executions without proper cleanup between switches
4. **No Fallback Mechanism**: When ctrld failed, no automatic DNS fallback was triggered

## Timeline Analysis

### 07:19:21 - Initial Gaming Switch Attempt
- Script executed `dns-gaming` successfully 
- ctrld appeared to start but couldn't verify Control D profile
- DNS queries working via `*********` but TXT verification timed out

### 07:22:06 - Second Gaming Switch 
- **Critical Warning Detected**: `Warning: PID 14640 is listening on :53 (not ctrld). This may conflict.`
- Windscribe identified as the conflicting process
- Health check failed: `❌ ctrld is NOT bound to port 53`

### 07:23:29 - Privacy Switch Attempt
- Script tried to switch to privacy mode
- Same port binding issues persisted

### 07:23:52 - Final Gaming Switch
- Process required SIGKILL: `ctrld (pid 17337) did not exit; sending SIGKILL...`
- Indicates ctrld was stuck/unresponsive

## Technical Evidence

### From ctrld logs (`/var/log/ctrld-gaming.log`):
```
Sep 11 07:22:07.221 ERR failed to resolve query error="could not perform request: Get \"https://*****.controld.com/1igcvpwtsfg?dns=...\": dial tcp *****:443: i/o timeout"
Sep 11 07:22:07.221 WRN upstream "upstream.0" marked as down immediately (failure count: 758)
Sep 11 07:22:49.237 FTL failed to fetch resolver config error="...context deadline exceeded..."
```

### From switching scripts analysis:
- Scripts hardcode listen address: `--listen "*********:53"`
- No conflict detection before attempting to bind port 53
- No rollback mechanism on failure
- DNS forced to `*********` regardless of ctrld's actual binding status

### Current System State (Post-Recovery):
- DNS working with external resolvers (*****, ****)
- No processes currently bound to port 53
- ctrld not running
- mDNSResponder properly bound to port 5353 (normal)

## Contributing Factors

1. **Lack of Port Binding Validation**: Scripts don't verify ctrld successfully binds to port 53
2. **VPN Integration Issues**: Windscribe and ctrld competing for the same privileged port
3. **No Service Management**: Ad-hoc process management instead of proper launchd integration
4. **Missing Health Checks**: No automated detection and fallback when DNS fails
5. **Race Conditions**: Rapid switching without proper cleanup delays

## Lessons Learned

1. **Port 53 is privileged** and multiple applications cannot bind to it simultaneously
2. **VPN applications often claim port 53** for their own DNS functionality
3. **System DNS settings are "dumb"** - they point to an IP:port regardless of what's listening
4. **Manual process management is fragile** - proper service management (launchd) is essential
5. **DNS failures are catastrophic** - require immediate fallback mechanisms

## Immediate Fixes Required

1. **Implement proper service conflict detection**
2. **Add comprehensive port binding validation** 
3. **Create robust fallback mechanisms**
4. **Separate VPN and DNS proxy modes explicitly**
5. **Add proper launchd service management**

---
*Investigation continues with systematic reproduction and solution implementation...*
