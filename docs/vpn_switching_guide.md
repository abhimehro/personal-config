# VPN Switching Guide: WARP+Control D ↔ ProtonVPN

This guide provides streamlined instructions for switching between Cloudflare WARP+Control D DNS and ProtonVPN configurations.

## Quick Reference

| Configuration | Command | Use Case |
|---------------|---------|----------|
| WARP+Control D | `vpn-normal` | General browsing, everyday use |
| ProtonVPN | `vpn-gaming` | Gaming, streaming, low-latency needs |
| Check Status | `vpn-status` | View current configuration |

## Detailed Workflow

### A. Switching to ProtonVPN for Gaming

```bash
# 1. Run the gaming configuration script
vpn-gaming
# This will:
# - Set WARP to the correct mode (proxy mode)
# - Disconnect WARP if connected
# - Reset DNS to automatic
# - Launch ProtonVPN for server selection

# 2. Select your preferred server in ProtonVPN
# (Dallas or Atlanta recommended for best gaming performance)
```

### B. Switching Back to WARP+Control D

```bash
# 1. Manually disconnect ProtonVPN first
# Open ProtonVPN app and click Disconnect

# 2. Run the restore script
vpn-normal
# This will:
# - Set WARP to tunnel_only mode
# - Configure DNS servers to use Control D
# - Connect WARP with proper settings
```

## Troubleshooting

### If WARP keeps reconnecting while using ProtonVPN:

1. Manually disconnect WARP:
   ```bash
   warp-cli disconnect
   ```

2. Set WARP to proxy mode (prevents auto-tunnel):
   ```bash
   warp-cli mode proxy
   ```

3. Restart your gaming script:
   ```bash
   vpn-gaming
   ```

### If Control D DNS isn't correctly applying:

1. Verify WARP is in tunnel_only mode:
   ```bash
   warp-cli mode tunnel_only
   ```

2. Restart the restore script:
   ```bash
   vpn-normal
   ```

3. Check DNS configuration:
   ```bash
   scutil --dns | grep "nameserver\[[0-9]*\]" | head -2
   ```
   *Should show: 76.76.2.22 and 76.76.2.23*

## Technical Details

- **WARP Modes:**
  - `tunnel_only`: Establishes a WARP tunnel without DNS proxying (used with Control D)
  - `proxy`: SOCKS5 proxy mode (prevents auto-reconnection when using ProtonVPN)

- **Control D DNS Servers:**
  - Primary: 76.76.2.22
  - Secondary: 76.76.2.23

- **ProtonVPN Recommended Servers:**
  - US-TX (Dallas) servers
  - US-GA (Atlanta) servers

## Additional Resources

Your system includes these monitoring tools:
- `check-warp`: Check connection status history
- `check-errors`: View errors and warnings in logs
- `monitor-net`: Live monitoring of network services
- `check-logs`: View recent log entries

---

*Last updated: April 11, 2025*

