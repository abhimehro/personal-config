# Control D + Windscribe VPN Integration Guide

## The DNS Conflict Problem

**CORE ISSUE**: Both Control D and Windscribe want to control DNS for security/privacy reasons, creating a conflict.

### What Each Service Does

**Control D (ctrld)**:
- Runs locally on port 53 (standard DNS port)
- Intercepts all DNS queries from your system
- Forwards queries to Control D's DoH endpoints
- Provides filtering, privacy, and malware protection

**Windscribe VPN**:
- Creates a VPN tunnel (utun interfaces)
- Routes all traffic through encrypted tunnel
- Has its own DNS servers for privacy
- Can be configured to use: local DNS, custom DNS, or Windscribe DNS

## Three Integration Scenarios

### Scenario 1: Windscribe with Local DNS (Uses Control D) ✅ RECOMMENDED

**Configuration**:
- Windscribe: Set to "Use local DNS"
- Control D: Running normally

**What happens**:
```
Your app → Windscribe tunnel → Control D (127.0.0.1:53) → DoH to Control D servers
```

**Pros**:
- ✅ Get both VPN encryption AND Control D filtering
- ✅ DNS queries encrypted twice (VPN tunnel + DoH)
- ✅ Control D's malware/tracker blocking works
- ✅ No DNS leaks

**Cons**:
- ⚠️ Slightly higher latency (double encryption)
- ⚠️ If Control D fails, DNS breaks completely

**Setup**:
```bash
# 1. Ensure Control D is running
sudo ctrld service status

# 2. Connect Windscribe
windscribe connect

# 3. Set Windscribe DNS preference
windscribe dns local

# 4. Verify DNS is working
dig example.com +short
```

**Verification**:
```bash
# Check VPN is active
windscribe status

# Check DNS goes through Control D
dig @127.0.0.1 example.com

# Check for DNS leaks
curl -s https://ipleak.net/json/ | jq -r '.ip, .dns_servers[]'
```

---

### Scenario 2: Windscribe with Custom DNS (Control D Endpoints) ✅ ALTERNATIVE

**Configuration**:
- Windscribe: Set custom DNS to Control D's DoH endpoints
- Control D: Can be disabled (not needed)

**What happens**:
```
Your app → Windscribe tunnel → Control D DoH endpoints directly
```

**Pros**:
- ✅ Get Control D filtering through VPN
- ✅ Lower latency (single encryption layer)
- ✅ Simpler setup
- ✅ No local Control D service needed

**Cons**:
- ⚠️ No failover if you switch profiles
- ⚠️ Manual config changes needed for profile switching
- ⚠️ Can't easily disable filtering temporarily

**Setup**:
```bash
# 1. Stop Control D (optional)
sudo ctrld service stop

# 2. Configure Windscribe with Control D endpoints
# Use Control D's DNS-over-HTTPS endpoints:
# Privacy Enhanced: https://freedns.controld.com/6m971e9jaf
# Browsing Privacy: https://freedns.controld.com/rcnz7qgvwg
# Gaming: https://freedns.controld.com/1xfy57w34t7

# 3. Connect VPN
windscribe connect
```

---

### Scenario 3: Windscribe DNS Only ⚠️ NOT RECOMMENDED

**Configuration**:
- Windscribe: Use Windscribe DNS
- Control D: Disabled

**What happens**:
```
Your app → Windscribe tunnel → Windscribe DNS
```

**Pros**:
- ✅ Simplest setup
- ✅ Guaranteed no DNS leaks
- ✅ Lowest latency

**Cons**:
- ❌ Lose Control D's filtering capabilities
- ❌ Less control over DNS behavior
- ❌ Can't switch between privacy profiles

---

## Potential Problems & Solutions

### Problem 1: DNS Not Resolving After Connecting VPN

**Symptoms**:
- Websites won't load
- `dig example.com` times out
- `curl` fails with "Could not resolve host"

**Diagnosis**:
```bash
# Check what DNS servers are active
scutil --dns | head -20

# Check if Control D is still listening
sudo lsof -i :53

# Check VPN status
windscribe status
```

**Solution A**: VPN is routing around Control D
```bash
# Tell Windscribe to use local DNS
windscribe dns local

# Restart VPN connection
windscribe disconnect
windscribe connect

# Verify
dig @127.0.0.1 example.com
```

**Solution B**: Control D stopped when VPN connected
```bash
# Restart Control D
sudo ctrld service restart

# Wait 3 seconds for startup
sleep 3

# Test
dig @127.0.0.1 example.com
```

---

### Problem 2: DNS Leaks (ISP Can See Queries)

**Symptoms**:
- DNS leak test shows ISP DNS servers
- Privacy compromised despite VPN

**Diagnosis**:
```bash
# Run DNS leak test
curl -s https://ipleak.net/json/ | jq -r '.dns_servers[]'

# Should show Control D or Windscribe IPs, NOT your ISP
```

**Solution**:
```bash
# Ensure Control D or Windscribe DNS is being used
windscribe dns local  # For Control D
# OR
windscribe dns custom <Control D endpoint>
```

---

### Problem 3: Control D Self-Checks Fail With VPN Active

**Symptoms**:
- `sudo ctrld start` fails with "connection refused"
- Service won't start when VPN is connected

**Solution**:
This is why we use `--skip_self_checks`:
```bash
# Already configured in your setup
sudo ctrld service start --config ~/.config/controld/ctrld.toml --skip_self_checks
```

The flag bypasses startup validation that fails due to VPN routing.

---

### Problem 4: Split Personality (Some Apps Use VPN DNS, Others Use Control D)

**Symptoms**:
- Inconsistent behavior between apps
- Some apps bypass filtering

**Diagnosis**:
```bash
# Check system DNS configuration
scutil --dns

# Look for multiple DNS resolvers
```

**Solution**:
```bash
# Reset DNS configuration
sudo dscacheutil -flushcache
sudo killall -HUP mDNSResponder

# Restart both services
sudo ctrld service restart
windscribe disconnect && windscribe connect
```

---

## Recommended Configuration Matrix

| Use Case | Control D | Windscribe DNS Setting | Why |
|----------|-----------|----------------------|-----|
| **Maximum Privacy + Filtering** | Running | Local DNS | Double encryption, full filtering |
| **Traveling/Untrusted Networks** | Running | Local DNS | Protects against MITM + malware |
| **Gaming** | Running (gaming profile) | Local DNS | Low latency filtering |
| **Streaming** | Disabled | Windscribe DNS | Avoid potential blocking |
| **Work VPN** | Running | Local DNS | Corporate VPN + threat protection |

---

## Testing Your Configuration

### Test 1: DNS Resolution Works
```bash
dig example.com +short
# Should return IP addresses
```

### Test 2: Control D Filtering Active
```bash
# Test against known malware domain (blocked by Control D)
dig malware.wicar.org @127.0.0.1
# Should return NXDOMAIN or Control D's block page IP
```

### Test 3: No DNS Leaks
```bash
# Check public DNS
curl -s https://ipleak.net/json/ | jq -r '.dns_servers[]'
# Should NOT show your ISP's DNS servers
```

### Test 4: VPN Active and Routing Correctly
```bash
# Check public IP (should be VPN location)
curl -s https://ipinfo.io/ip

# Check routing
netstat -rn | grep default
# Should show utun interface
```

---

## Startup Order Considerations

**Order matters!** Here's the recommended sequence:

### On System Boot:
1. ✅ Control D auto-starts (via Launch Daemon)
2. ✅ Wait 5-10 seconds for DNS to stabilize
3. ✅ Connect Windscribe VPN
4. ✅ System uses Control D for DNS, Windscribe for routing

### Manual Connection:
```bash
# If Control D is running and you want to connect VPN:
sudo ctrld service status  # Verify running
windscribe connect

# If VPN is connected and you want to start Control D:
sudo ctrld service start --config ~/.config/controld/ctrld.toml --skip_self_checks
windscribe disconnect && windscribe connect  # Reconnect to apply DNS changes
```

---

## Troubleshooting Checklist

When things go wrong with VPN + Control D:

- [ ] Control D service is running: `sudo ctrld service status`
- [ ] Windscribe is connected: `windscribe status`
- [ ] Windscribe DNS set to local: `windscribe dns local`
- [ ] DNS resolves: `dig example.com +short`
- [ ] No DNS leaks: `curl -s https://ipleak.net/json/ | jq -r '.dns_servers[]'`
- [ ] VPN tunnel active: `ifconfig | grep utun`
- [ ] Firewall not blocking: `sudo /usr/libexec/ApplicationFirewall/socketfilterfw --listapps | grep ctrld`

---

## Emergency Recovery

**If everything breaks:**

```bash
# 1. Disconnect VPN
windscribe disconnect

# 2. Stop Control D
sudo ctrld service stop

# 3. Flush DNS cache
sudo dscacheutil -flushcache
sudo killall -HUP mDNSResponder

# 4. Verify system DNS works
dig example.com +short
# Should work using router/ISP DNS

# 5. Restart in order
sudo ctrld service start --config ~/.config/controld/ctrld.toml --skip_self_checks
sleep 5
windscribe connect
windscribe dns local

# 6. Test
dig example.com +short
```

---

## Security Considerations

### DNS Query Path Analysis

**Without VPN**:
```
App → Control D (local) → DoH (encrypted) → Control D servers → Internet
```
- ✅ ISP can't see DNS queries (DoH encrypted)
- ⚠️ ISP can see destination IPs
- ✅ Control D filtering active

**With VPN + Local DNS**:
```
App → Control D (local) → VPN tunnel (encrypted) → DoH (encrypted) → Control D servers → Internet
```
- ✅ ISP can't see DNS queries (double encrypted)
- ✅ ISP can't see destination IPs (VPN tunnel)
- ✅ Control D filtering active
- ✅ Maximum privacy

### Attack Surface

**Threat Model**:
1. **MITM on DNS** → Prevented by DoH + VPN
2. **DNS Hijacking** → Prevented by local Control D + encrypted tunnel
3. **ISP Surveillance** → Prevented by VPN tunnel
4. **Malware/Phishing** → Prevented by Control D filtering
5. **DNS Leaks** → Prevented by proper Windscribe config

---

## Integration with Maintenance System

Add to your weekly maintenance (`~/Public/Scripts/maintenance/`):

```bash
# Add to run_all_maintenance.sh or create separate check:
echo "Checking Control D + VPN integration..."
~/Public/Scripts/maintenance/controld_monitor.sh

# Check for DNS leaks if VPN is active
if windscribe status | grep -q "Connected"; then
    echo "VPN active - checking for DNS leaks..."
    DNS_SERVERS=$(curl -s https://ipleak.net/json/ 2>/dev/null | jq -r '.dns_servers[]')
    if echo "$DNS_SERVERS" | grep -q "comcast\|att\|verizon\|spectrum"; then
        echo "⚠️  WARNING: Potential DNS leak detected!"
    fi
fi
```

---

## Future-Proofing

### When Upgrading ctrld
```bash
# Upgrade via Homebrew
brew upgrade ctrld

# Service config persists (launch daemon unchanged)
# Verify it still works
sudo ctrld service status
~/.config/controld/health-check.sh
```

### When Changing VPN Providers
If you switch from Windscribe to another VPN:
1. Configure new VPN to use local DNS (127.0.0.1)
2. Test: `dig @127.0.0.1 example.com`
3. Verify no DNS leaks
4. Update this documentation

### When Switching Control D Profiles
```bash
# Edit config
nano ~/.config/controld/ctrld.toml
# Change: upstream = ["gaming_optimized"]  # or other profile

# Restart
sudo ctrld service restart

# If VPN is connected, reconnect
windscribe disconnect && windscribe connect
```

---

## Additional Resources

- Control D VPN Integration Docs: https://docs.controld.com/docs/vpn-integration
- Windscribe DNS Settings: https://windscribe.com/features/flexible-connectivity
- DNS Leak Test: https://ipleak.net
- Your configs: `~/.config/controld/`
