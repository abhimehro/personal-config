# Control D Quick Start

## First Time Setup
```bash
# Start Control D with privacy profile (default)
sudo ctrld start --config ~/.config/controld/ctrld.toml

# Verify it's running
sudo ctrld status
```

## Switch Profiles
```bash
ctrld-switch privacy   # Max security
ctrld-switch browsing  # Balanced
ctrld-switch gaming    # Min filtering
```

## Quick Commands
```bash
sudo ctrld stop        # Stop service
sudo ctrld restart     # Restart service
sudo ctrld status      # Check status
sudo ctrld reload      # Apply config changes
```

## Current Profile
```bash
cat ~/.config/controld/ctrld.toml | grep "upstream ="
```

## Test DNS
```bash
nslookup google.com 127.0.0.1
```

## Logs
```bash
sudo tail -f /var/log/ctrld.log
```

---
**Read full docs:** `cat ~/.config/controld/README.md`
