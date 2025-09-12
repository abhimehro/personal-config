# DNS Configuration Guide

## 🏗️ Architecture Overview

Our DNS solution uses a layered approach:

```
Internet Queries → ctrld (127.0.0.1:53) → DoH3/QUIC → Control D → Internet
Local Queries   → ctrld (127.0.0.1:53) → Plain DNS → Local Router → Local Network
Dev Queries     → ctrld (127.0.0.1:53) → Localhost → 127.0.0.1
```

## 📋 Configuration Files

### 1. Main Configuration: `ctrld-enhanced-split-dns.toml`

**Location**: `/etc/controld/ctrld.toml`  
**Backup**: `dns-setup/configs/ctrld-enhanced-split-dns.toml`

> Tip: Set your Control D profile ID in environment: `export CTRLD_PROFILE_ID=xxxxxxxxxx` and reference it in configs.

Key sections:

#### Listener Configuration
```toml
[listener]
  [listener.0]
    ip = '127.0.0.1'    # Bind to localhost only
    port = 53           # Standard DNS port
```

#### Split-DNS Rules
```toml
# Local network domains → Router
{ '*.local' = ['192.168.4.1']},
{ '*.lan' = ['192.168.4.1']},
{ '*.home.arpa' = ['192.168.4.1']},

# Development domains → Localhost  
{ '*.test' = ['127.0.0.1']},
{ '*.dev' = ['127.0.0.1']},
{ '*.localhost' = ['127.0.0.1']},
```

#### Upstream Configuration
```toml
[upstream.0]
type = 'doh3'                                    # HTTP/3 over QUIC
endpoint = 'https://dns.controld.com/${CTRLD_PROFILE_ID}'  # Your Control D profile
bootstrap_ip = '76.76.19.19'                    # Pre-resolved Control D IP
timeout = 5000                                   # 5 second timeout

[upstream.1] 
type = 'plain'              # Fallback for local queries
endpoint = '192.168.4.1:53' # Your local router
timeout = 2000              # 2 second timeout for local
```

### 2. Maintenance Daemon: `com.controld.maintenance.plist`

**Location**: `/Library/LaunchDaemons/com.controld.maintenance.plist`  
**Schedule**: Daily at 3:00 AM  
**Function**: Health checks, performance monitoring, backups

```xml
<key>StartCalendarInterval</key>
<dict>
    <key>Hour</key>
    <integer>3</integer>
    <key>Minute</key>
    <integer>0</integer>
</dict>
```

## 🔧 Service Management

### Control D Service (ctrld)
- **Binary**: `/usr/local/bin/ctrld`
- **Config**: `/etc/controld/ctrld.toml`  
- **Service**: `system/ctrld` (launchd)
- **Logs**: System logs via `log show --predicate 'process == "ctrld"'`

### Maintenance Service
- **Script**: `/usr/local/bin/controld-maintenance`
- **Config**: `/Library/LaunchDaemons/com.controld.maintenance.plist`
- **Logs**: `/var/log/controld-maintenance.log`
- **Performance**: `/var/log/controld-performance.log`

## 🌐 Network Integration

### macOS DNS Configuration
```bash
# Primary interface
networksetup -setdnsservers "Wi-Fi" 127.0.0.1

# Verify configuration  
scutil --dns | grep "nameserver"
```

### System Resolver Order
1. **127.0.0.1:53** (ctrld) - Primary
2. **System default** - Fallback if ctrld fails
3. **Emergency fallback** - Via maintenance script

## 📊 Protocol Details

### DoH3 (DNS-over-HTTPS version 3)
- **Protocol**: HTTP/3 over QUIC (UDP 443)
- **Encryption**: TLS 1.3 with 0-RTT capability
- **Performance**: ~30% faster than DoH/DoH2
- **Fallback**: Automatic fallback to DoH (HTTP/2) if QUIC fails

### Split-DNS Logic
```
Query for *.local     → 192.168.4.1:53 (Plain DNS)
Query for *.test      → 127.0.0.1 (Local resolution)  
Query for google.com  → Control D via DoH3 (Filtered)
Query for ads.com     → Control D via DoH3 (Blocked)
```

## 🔍 Monitoring & Logging

### Health Monitoring
- **Service Status**: Process verification (PID check)
- **Port Binding**: Confirm 127.0.0.1:53 listener active
- **DNS Resolution**: Test query to google.com
- **Upstream Connectivity**: Verify Control D connection

### Performance Tracking  
- **Query Times**: Measure DNS resolution speed
- **Cache Efficiency**: Track cache hit/miss ratios
- **Network Latency**: Monitor upstream latency
- **Error Rates**: Count failed queries

### Log Files
```bash
# Maintenance logs
tail -f /var/log/controld-maintenance.log

# Performance metrics
tail -f /var/log/controld-performance.log  

# System logs (ctrld)
log stream --predicate 'process == "ctrld"' --info
```

## 🛠️ Customization Options

### Adding Custom Split-DNS Rules
Edit `/etc/controld/ctrld.toml`:
```toml
# Corporate domains → Company DNS
{ '*.corp.company.com' = ['10.0.1.1']},

# IoT devices → Router  
{ '*.iot' = ['192.168.4.1']},
```

### Performance Tuning
```toml
[upstream.0]
timeout = 3000        # Faster timeout for DoH3
max_conns = 8         # More concurrent connections

# Cache settings (if supported)
cache_size = 1000     # Larger cache
cache_ttl = 3600      # 1 hour cache TTL
```

### Custom Maintenance Schedule
Edit `/Library/LaunchDaemons/com.controld.maintenance.plist`:
```xml
<!-- Run every 6 hours -->
<key>StartInterval</key>
<integer>21600</integer>
```

## 🔧 Advanced Configuration

### Bootstrap IP Management
The bootstrap IP prevents circular DNS dependencies when resolving the DoH3 endpoint:

```bash
# Update bootstrap IP if Control D changes infrastructure
dig +short dns.controld.com @8.8.8.8
# Update ctrld.toml with new IP
```

### Captive Portal Bypass
Our configuration includes comprehensive captive portal rules for travel:
- Airline WiFi (United, Delta, American, etc.)
- Hotel chains and public WiFi
- International networks (European trains, etc.)

### Emergency Fallback Configuration
```toml
# Add emergency upstream as upstream.2
[upstream.2]
type = 'plain'
endpoint = '1.1.1.1:53'  # Cloudflare fallback
timeout = 1000           # Fast timeout
```

---

> **Security Note**: All DNS queries are encrypted via DoH3/QUIC. Local domain queries use plain DNS to your router for performance, but these never leave your local network.

> **Performance Note**: This configuration is optimized for macOS 13+ with full HTTP/3 support. For older systems, DoH3 will automatically fallback to DoH (HTTP/2).
