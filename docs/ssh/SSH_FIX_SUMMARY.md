> **NOTE (2026):** This fix summary documents an earlier Cursor/1Password-only
> configuration. Hostnames have since been generalized to `dev-*` and Proton
> Pass is supported as a second SSH agent (see `README.md`).

# SSH Configuration Fix Summary

## Issues Found and Fixed

### Problem
SSH config had placeholder values that prevented connections:
- `__USERNAME__` → Needed to be replaced with actual username
- `<mdns-hostname>` → Needed to be replaced with actual mDNS hostname
- `<local-hostname>` → Needed to be replaced with actual hostname

### Solution
Updated SSH config with your system values:
- **Username**: `abhimehrotra`
- **mDNS Hostname**: `abhis-macbook-air.local`
- **Local Hostname**: `abhis-macbook-air.local` (mDNS works better than direct hostname)

## Updated SSH Hosts

### ✅ cursor-mdns (Recommended)
- **Hostname**: `abhis-macbook-air.local`
- **User**: `abhimehrotra`
- **Best for**: Any network (works with/without VPN)
- **Usage**: `ssh cursor-mdns`

### ✅ cursor-local
- **Hostname**: `abhis-macbook-air.local`
- **User**: `abhimehrotra`
- **Best for**: Local network only
- **Usage**: `ssh cursor-local`

### ✅ cursor-auto
- **Hostname**: `abhis-macbook-air.local`
- **User**: `abhimehrotra`
- **Best for**: Auto-detection fallback
- **Usage**: `ssh cursor-auto`

### ⚠️ cursor-vpn
- **Hostname**: `<vpn-ip-address>` (placeholder - replace when needed)
- **User**: `abhimehrotra`
- **Best for**: VPN connections
- **Usage**: Replace `<vpn-ip-address>` with your VPN IP when needed

## Testing

All connection methods tested and working:
```bash
./scripts/test_ssh_connections.sh
```

Results:
- ✅ cursor-mdns: Connection successful
- ✅ cursor-local: Connection successful
- ✅ cursor-auto: Connection successful

## Using in Cursor IDE

### Remote SSH Connection

1. **Open Cursor Settings**:
   - Press `Cmd+,` (or `Ctrl+,` on Windows/Linux)
   - Search for "Remote SSH"

2. **Add SSH Host**:
   - Press `Cmd+Shift+P` (or `Ctrl+Shift+P`)
   - Type "Remote-SSH: Connect to Host"
   - Select `cursor-mdns` (or `cursor-local`, `cursor-auto`)

3. **First Connection**:
   - Cursor will prompt to accept the host key
   - Enter your password (or use SSH key authentication)
   - Cursor will open a new window connected to your MacBook Air

### Recommended Host for Cursor

Use **`cursor-mdns`** as it:
- Works on any network (local or VPN)
- Uses mDNS/Bonjour for reliable discovery
- Has optimal settings for remote development

## Verification

Test your SSH config:
```bash
# Test config parsing
ssh -G cursor-mdns

# Test connection (will prompt for host key first time)
ssh cursor-mdns

# Test with verbose output for debugging
ssh -v cursor-mdns
```

## Troubleshooting

### "Host key verification failed"
**Solution**: Accept the host key on first connection:
```bash
ssh cursor-mdns
# Type "yes" when prompted
```

### "Permission denied"
**Solution**: Ensure SSH keys are set up:
```bash
# Check if 1Password SSH agent is running
ls -la ~/Library/Group\ Containers/2BUA8C4S2C.com.1password/t/agent.sock

# Check SSH keys
ssh-add -l
```

### "Connection refused"
**Solution**: Enable Remote Login on macOS:
1. System Settings → General → Sharing
2. Enable "Remote Login"
3. Allow access for your user

### "Connection timed out"
**Solution**: Check network connectivity:
```bash
ping abhis-macbook-air.local
```

## Notes

- All hosts use **1Password SSH Agent** for key management
- **Connection multiplexing** is enabled for faster reconnections
- **Control D** network functions work independently of SSH
- Config is symlinked: `~/.ssh/config` → `configs/ssh/config`
