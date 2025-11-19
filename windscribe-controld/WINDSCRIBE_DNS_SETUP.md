# Windscribe DNS Configuration for Control D Integration

> **Note (v4.x):** This document captures earlier experiments and tuning around
> Windscribe DNS behavior. The current separation strategy relies on
> `scripts/network-mode-manager.sh` + `controld-manager`; treat this file as
> historical/advanced reference rather than the main setup path.

## Current Status
✅ **Control D Service**: Running with VPN-compatible binding (`*:53`)  
✅ **Windscribe VPN**: Connected (Dallas, US)  
❌ **DNS Filtering**: Not active (VPN overriding Control D DNS)

## Problem Diagnosis
Windscribe VPN is using its own DNS servers (`1.1.1.1`) instead of Control D (`127.0.0.1`), preventing ad blocking and privacy filtering.

## Solution Options

### Option 1: Windscribe App Settings (PREFERRED)

1. **Open Windscribe Desktop App**
2. **Go to Preferences → Connection**
3. **DNS Settings:**
   - **DNS**: Set to `Local DNS` ✅
   - **App Internal DNS**: Try these options in order:
     - First try: `Control D` (if available in dropdown)
     - If not available: `Custom` → Enter `127.0.0.1`
     - Last resort: `OS Default`
4. **Split Tunneling**: `OFF` ✅
5. **Click Apply/Save**
6. **Disconnect and reconnect Windscribe**

### Option 2: Custom DNS Override (ACTIVE)

If Windscribe settings don't work, we've implemented a DNS override:

```bash
# Enable Control D DNS priority (already done)
sudo ~/Documents/dev/personal-config/windscribe-controld/fix-dns-priority.sh enable

# Test if filtering is active
~/Documents/dev/personal-config/windscribe-controld/test-vpn-integration.sh

# If issues occur, disable override
sudo ~/Documents/dev/personal-config/windscribe-controld/fix-dns-priority.sh disable
```

### Option 3: Alternative VPN DNS Settings

Try these Windscribe DNS configurations:

1. **DNS**: `Local DNS` + **App Internal DNS**: `127.0.0.1` (custom)
2. **DNS**: `Control D` (if available) + **App Internal DNS**: `OS Default`  
3. **DNS**: `Custom` (`127.0.0.1`) + **App Internal DNS**: `OS Default`

## Verification Steps

After changing Windscribe settings:

1. **Disconnect Windscribe VPN**
2. **Reconnect Windscribe VPN**
3. **Run integration test:**
   ```bash
   ~/Documents/dev/personal-config/windscribe-controld/test-vpn-integration.sh
   ```

### Expected Results
```
✅ Control D service: RUNNING
✅ VPN interface: CONNECTED
✅ Ad blocking: ACTIVE (doubleclick.net → 127.0.0.1)
✅ Normal DNS: WORKING
✅ VPN location: [City], [Country]
🟢 PERFECT! Windscribe + Control D working together
```

## Troubleshooting

### DNS Filtering Not Working
- Check Windscribe "App Internal DNS" setting
- Try disconnecting/reconnecting VPN
- Flush DNS cache:
  ```bash
  sudo ~/Documents/dev/personal-config/windscribe-controld/fix-dns-priority.sh flush
  ```

### VPN Connection Issues
- Ensure Control D service is running:
  ```bash
  sudo ~/Documents/dev/personal-config/windscribe-controld/controld-service-manager.sh status
  ```
- Restart Control D if needed:
  ```bash
  sudo ~/Documents/dev/personal-config/windscribe-controld/controld-service-manager.sh restart
  ```

### Complete Reset
If nothing works:

1. **Disable DNS override:**
   ```bash
   sudo ~/Documents/dev/personal-config/windscribe-controld/fix-dns-priority.sh disable
   ```

2. **Stop Control D:**
   ```bash
   sudo ~/Documents/dev/personal-config/windscribe-controld/controld-service-manager.sh stop
   ```

3. **Disconnect Windscribe VPN**

4. **Restart Control D:**
   ```bash
   sudo ~/Documents/dev/personal-config/windscribe-controld/controld-service-manager.sh start
   ```

5. **Reconnect Windscribe VPN** with correct DNS settings

## Success Indicators

### ✅ Working Configuration
- **Ad domains blocked**: `doubleclick.net` → `127.0.0.1`
- **Normal sites work**: `google.com` resolves correctly
- **VPN location**: Shows VPN server location
- **DNS filtering**: Visible in Control D dashboard

### ❌ Issues
- Ad domains resolve to real IPs (not `127.0.0.1`)
- DNS queries not appearing in Control D dashboard
- VPN connection failures

## Alternative: Profile Switching

You can also test different Control D profiles while VPN is connected:

```bash
# Switch to Gaming profile (less filtering)
sudo controld-manager switch gaming

# Switch back to Privacy profile (full filtering)  
sudo controld-manager switch privacy

# Test after switching
~/Documents/dev/personal-config/windscribe-controld/test-vpn-integration.sh
```

## Emergency Commands

```bash
# Check Control D status
sudo ~/Documents/dev/personal-config/windscribe-controld/controld-service-manager.sh status

# Test integration
~/Documents/dev/personal-config/windscribe-controld/test-vpn-integration.sh

# Enable DNS priority
sudo ~/Documents/dev/personal-config/windscribe-controld/fix-dns-priority.sh enable

# Disable DNS priority
sudo ~/Documents/dev/personal-config/windscribe-controld/fix-dns-priority.sh disable
```