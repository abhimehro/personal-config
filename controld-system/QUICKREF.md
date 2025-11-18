# Control D Quick Reference

## Daily Commands

```bash
# Check service status
sudo ctrld service status

# View live logs
sudo tail -f /var/log/ctrld.log

# Run health check
~/.config/controld/health-check.sh

# Test DNS resolution
dig @127.0.0.1 example.com +short
```

## Profile Switching

```bash
# Use the profile switcher (if available)
ctrld-switch privacy    # Maximum security
ctrld-switch browsing   # Balanced
ctrld-switch gaming     # Low latency

# OR edit config manually
nano ~/.config/controld/ctrld.toml
# Change: upstream = ["privacy_enhanced"]
sudo ctrld service restart
```

## Troubleshooting

### Service won't start
```bash
# Check if it's a self-check issue
sudo ctrld start --config ~/.config/controld/ctrld.toml --skip_self_checks

# Reinstall service
sudo ctrld service stop
sudo ctrld service start --config ~/.config/controld/ctrld.toml --skip_self_checks
```

### DNS not resolving
```bash
# Check service status
sudo ctrld service status

# Check logs for errors
sudo tail -20 /var/log/ctrld.log | grep error

# Restart service
sudo ctrld service restart
```

### After system updates
```bash
# Verify firewall exception still exists
sudo /usr/libexec/ApplicationFirewall/socketfilterfw --listapps | grep ctrld

# Re-add if missing
sudo /usr/libexec/ApplicationFirewall/socketfilterfw --add /opt/homebrew/bin/ctrld
```

## Important Notes

- **Auto-start**: Service automatically starts on boot via Launch Daemon
- **Skip self-checks**: Required due to firewall timing during startup
- **Security**: DoH encryption protects DNS queries once service is running
- **Logs**: Main log at `/var/log/ctrld.log`
- **Config**: Located at `~/.config/controld/ctrld.toml`

## Emergency: Disable Control D

```bash
# Stop service
sudo ctrld service stop

# System DNS will fall back to default (DHCP-provided)
```

## Files to Backup

```bash
~/.config/controld/ctrld.toml          # Main config
~/.config/controld/README.md           # Full documentation
~/.config/controld/health-check.sh     # Health monitoring
/Library/LaunchDaemons/ctrld.plist     # Auto-start config
```
