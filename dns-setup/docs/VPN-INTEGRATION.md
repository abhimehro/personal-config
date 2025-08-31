# Windscribe VPN Integration Guide

## 🔗 Overview

This guide covers the integration of Control D DNS filtering with Windscribe VPN to provide comprehensive privacy and security. The setup ensures DNS queries are filtered by Control D while traffic is routed through Windscribe's secure VPN tunnels.

## ⚙️ Windscribe Configuration

### DNS Settings (Critical)

In Windscribe → **Preferences** → **Connection** → **DNS**:

```
App Internal DNS: Control D
```

**Why this matters**: This prevents VPN-aware applications from bypassing Control D filtering by using alternative DNS resolution methods.

### Split Tunneling Configuration

**Recommended Approach**: Exclude system DNS components from VPN tunneling while routing web traffic through the VPN.

#### Applications/Services to Exclude:
- **mDNSResponder** (system DNS service)
- **ctrld** (Control D DNS proxy) 
- **Local network ranges** (192.168.x.x, 10.x.x.x, 172.16-31.x.x)
- **System utilities** (ping, dig, nslookup)

#### Applications to Route Through VPN:
- **Web browsers** (Chrome, Safari, Firefox)
- **Email clients** 
- **Most internet applications**

### Protocol Configuration (WireGuard Recommended)
**Protocol**: **WireGuard**  
**Port**: **443** (optimal for most networks)

**Why WireGuard + Port 443**:
- **Performance**: WireGuard offers 20-30% better performance than OpenVPN
- **Battery Life**: More efficient on macOS, extends battery life
- **Reliability**: Less likely to be blocked by corporate/public networks
- **Port 443**: HTTPS port, rarely blocked by firewalls
- **Speed**: Faster connection establishment and data transfer
- **Stability**: Better handling of network changes and reconnections

**Alternative Port Options**:
- **Port 1194** - Traditional VPN port (may be blocked)
- **Port 53** - DNS port (avoid - conflicts with our Control D setup)
- **Port 80** - HTTP port (good fallback if 443 is blocked)

### Proxy Settings
**Recommendation**: **Disabled**

Control D already provides encrypted DNS via DoH3 (HTTP/3 over QUIC). Additional HTTP proxy layers can:
- Reduce performance
- Create connection conflicts
- Add unnecessary complexity

## 🛡️ Security Integration

### DNS Leak Prevention

Our setup prevents DNS leaks through multiple layers:

1. **System-level DNS Override**: All DNS queries forced through 127.0.0.1
2. **App Internal DNS Setting**: Applications use Control D instead of VPN DNS
3. **Binding to Localhost**: ctrld binds directly to 127.0.0.1:53

### Verification Commands

```bash
# Verify DNS resolution path
dig +short whoami.akamai.net @127.0.0.1

# Check for DNS leaks (should show VPN IP, resolved via Control D)
curl -s https://1.1.1.1/cdn-cgi/trace | grep ip=

# Verify Control D filtering is active
nslookup ads.example.com 127.0.0.1  # Should block/redirect
```

## 🔀 Traffic Flow Architecture

```
Application Request
        ↓
   System DNS (127.0.0.1:53)
        ↓
    ctrld DNS Proxy
        ↓
   ┌─── Local Domain? ───┐
   ↓                     ↓
Router DNS          Control D
(*.local, *.test)   (Internet domains)
        ↓                 ↓
   Local Response    DoH3 Encryption
                          ↓
                    Control D Servers
                          ↓
                    Filtered Response
                          ↓
                    Application
                          ↓
                    Windscribe VPN
                          ↓
                    Internet Traffic
```

## 📊 Performance Optimization

### DNS Query Performance
With the integrated setup:
- **Cold queries**: 80-120ms (via Control D DoH3)
- **Cached queries**: <20ms (local cache)
- **Local domain queries**: 20-50ms (via router)

### VPN Performance Impact
- **DNS Resolution**: Minimal impact (encrypted tunnel separate)
- **Web Browsing**: Standard VPN latency applies
- **Local Network**: No VPN routing (maintains local speed)

## 🔧 Configuration Verification

### Post-VPN Connection Tests

After connecting to Windscribe:

```bash
# 1. Verify DNS still resolves locally
nslookup google.com 127.0.0.1

# 2. Check Control D filtering
dig blocked-domain.com @127.0.0.1

# 3. Verify VPN IP assignment  
curl -s ifconfig.me  # Should show VPN server IP

# 4. Confirm no DNS leaks
curl -s https://1.1.1.1/cdn-cgi/trace | grep ip=  # Should match VPN IP

# 5. Test split-DNS routing
dig myapp.test @127.0.0.1     # Local development
dig printer.local @127.0.0.1  # Local network device
```

## 🚨 Troubleshooting

### Common Issues & Solutions

#### Issue: DNS Queries Slow After VPN Connection
**Symptoms**: DNS resolution takes >500ms
**Solution**:
```bash
# Restart ctrld service
sudo controld-maintenance restart

# Verify DoH3 connections
sudo lsof -i | grep ctrld
```

#### Issue: Local Domains Not Resolving
**Symptoms**: `myapp.test` or `printer.local` fail to resolve
**Solution**:
```bash
# Check split-DNS configuration
sudo cat /etc/controld/ctrld.toml | grep -A5 "rule"

# Verify router connectivity
ping $(netstat -rn | grep default | awk '{print $2}' | head -1)
```

#### Issue: DNS Leaks Detected
**Symptoms**: DNS queries bypass Control D, detected by online leak tests
**Solution**:
```bash
# Verify system DNS settings
scutil --dns | grep nameserver

# Should show only 127.0.0.1
# If not, reset:
sudo networksetup -setdnsservers "Wi-Fi" 127.0.0.1
sudo dscacheutil -flushcache
```

#### Issue: Control D Filtering Not Working
**Symptoms**: Ads/blocked content still loads
**Solution**:
```bash
# Test Control D connection
dig +short whoami.akamai.net @127.0.0.1

# Verify ctrld upstream config
sudo controld-maintenance health

# Check for bypass applications
sudo lsof -i :53  # Should only show ctrld
```

### Emergency Procedures

#### Complete DNS Failure
```bash
# Emergency fallback to public DNS
sudo controld-maintenance emergency

# This will:
# 1. Stop ctrld service  
# 2. Set DNS to 1.1.1.1, 8.8.8.8
# 3. Flush DNS cache
# 4. Provide recovery instructions
```

#### VPN Connection Issues
```bash
# Disconnect VPN, test DNS
sudo controld-maintenance health

# Reconnect VPN, retest
# DNS should continue working normally
```

## 📈 Performance Monitoring

### Automated Monitoring

The system automatically monitors integration health:

```bash
# Daily maintenance includes VPN integration tests
sudo controld-maintenance full

# View VPN-specific logs
sudo tail -50 /var/log/controld-performance.log | grep -i vpn
```

### Manual Performance Testing

```bash
# DNS performance with VPN connected
for i in {1..5}; do
  echo "Test $i:"
  time nslookup google.com 127.0.0.1 >/dev/null
done

# Compare with VPN disconnected
# Minimal difference indicates proper integration
```

## 🔐 Security Best Practices

### Recommended Settings Summary

| Component | Setting | Value | Purpose |
|-----------|---------|-------|---------|
| Windscribe DNS | App Internal DNS | Control D | Prevent DNS bypass |
| Windscribe Protocol | VPN Protocol | WireGuard | Best performance |
| Windscribe Port | Connection Port | 443 | Firewall compatibility |
| Windscribe Split | Exclude DNS utilities | Yes | Maintain local resolution |
| Windscribe Proxy | HTTP Proxy | Disabled | Avoid conflicts |
| System DNS | Primary | ********* | Force through Control D |
| ctrld Protocol | Upstream | DoH3 | Maximum encryption |

### Privacy Verification

```bash
# Complete privacy check
echo "=== Privacy Verification ==="
echo "IP Address: $(curl -s ifconfig.me)"
echo "DNS Server: $(dig +short whoami.akamai.net @127.0.0.1)"
echo "DNS Leak Test: $(curl -s https://1.1.1.1/cdn-cgi/trace | grep ip=)"
echo "Control D Active: $(dig +short test.controld.com @127.0.0.1)"
```

Expected results:
- IP Address: Shows VPN server IP
- DNS Server: Shows VPN server IP (resolved via Control D)
- DNS Leak Test: Matches VPN server IP  
- Control D Active: Returns Control D verification response

## 📋 Integration Checklist

### Pre-VPN Connection
- [ ] Control D service running (`sudo controld-maintenance health`)
- [ ] DNS set to 127.0.0.1 (`scutil --dns`)
- [ ] Split-DNS rules configured
- [ ] Local domains resolving (`dig myapp.test @127.0.0.1`)

### Post-VPN Connection  
- [ ] DNS still resolves through 127.0.0.1
- [ ] Control D filtering active (test blocked site)
- [ ] No DNS leaks detected
- [ ] VPN IP assigned correctly
- [ ] Local domains still accessible

### Weekly Verification
- [ ] DNS performance within normal range
- [ ] No DNS leak detection
- [ ] Control D filtering effectiveness
- [ ] VPN connection stability
- [ ] Local network access maintained

---

> **Security Note**: This integration provides defense-in-depth: Control D handles DNS filtering and encryption, while Windscribe protects traffic routing. Both work independently and complement each other.

> **Performance Tip**: The DoH3 upgrade and split-DNS configuration ensure optimal performance whether the VPN is connected or disconnected.
