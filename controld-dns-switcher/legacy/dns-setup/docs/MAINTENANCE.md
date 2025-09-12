# Maintenance Guide

## 🔧 Daily Operations

### Automated Maintenance
The system runs automated maintenance daily at 3:00 AM via launchd:

- ✅ Health checks (service status, DNS resolution)  
- ✅ Performance monitoring (query times, latency)
- ✅ Configuration backups (timestamped, rotated)
- ✅ Update notifications (new Control D versions)
- ✅ Network diagnostics (DNS leak detection)

### Manual Health Check
```bash
# Quick system status
sudo controld-maintenance health

# Expected output:
# ✅ ctrld service is running (PID: XXXXX)
# ✅ ctrld is bound to port 53
# ✅ DNS resolution working
# ✅ Active upstream connections: 1-2
```

## 📊 Performance Monitoring

### DNS Query Performance
```bash
# Performance test suite
sudo controld-maintenance performance

# Manual performance check
dig +stats google.com @127.0.0.1 | grep "Query time"
```

**Healthy Performance Metrics:**
- Query Time: 50-150ms (first query)
- Query Time: <50ms (cached queries)  
- Upstream Connections: 1-2 active
- Service Memory: <20MB RAM
- CPU Usage: <1%

### Performance Logs
```bash
# View performance history  
tail -100 /var/log/controld-performance.log

# Monitor real-time performance
watch -n 5 'dig +stats github.com @127.0.0.1 | grep "Query time"'
```

## 🔍 System Monitoring

### Service Status
```bash
# Check ctrld service
sudo launchctl list | grep ctrld
sudo lsof -i :53 | grep ctrld

# Check maintenance daemon
sudo launchctl list | grep controld.maintenance
```

### Network Connectivity
```bash
# Verify upstream connections
sudo lsof -i | grep ctrld

# Test DNS resolution paths
nslookup google.com 127.0.0.1        # Internet domain
dig myapp.test @127.0.0.1 +short     # Development domain  
dig printer.local @127.0.0.1 +short  # Local network domain
```

### DNS Leak Detection
```bash
# Verify no DNS leakage
dig +short whoami.akamai.net @127.0.0.1

# Test with VPN connected
# (Should still resolve through local 127.0.0.1)
```

## 🗄️ Backup Management

### Configuration Backups
**Location**: `/etc/controld/backups/`  
**Rotation**: Keeps latest 10 backups  
**Schedule**: Daily + on-demand

```bash  
# Manual backup
sudo controld-maintenance backup

# List available backups
sudo ls -la /etc/controld/backups/

# Restore from backup (if needed)
sudo cp /etc/controld/backups/ctrld.toml.TIMESTAMP /etc/controld/ctrld.toml
sudo launchctl kickstart -k system/ctrld
```

### Log Management
```bash
# View maintenance logs
sudo tail -100 /var/log/controld-maintenance.log

# View performance logs  
sudo tail -100 /var/log/controld-performance.log

# View scheduled maintenance
sudo tail -50 /var/log/controld-maintenance-scheduled.log
```

## 🔄 Service Management

### Safe Service Restart
```bash
# Recommended method (includes backup)
sudo controld-maintenance restart

# Manual restart (if needed)
sudo launchctl kickstart -k system/ctrld
```

### Configuration Updates
```bash
# 1. Backup current config
sudo controld-maintenance backup

# 2. Edit configuration  
sudo nano /etc/controld/ctrld.toml

# 3. Restart service
sudo controld-maintenance restart

# 4. Verify health
sudo controld-maintenance health
```

### Update Management
```bash
# Check for ctrld updates
sudo controld-maintenance full | grep "Update"

# Update ctrld (when available)
curl -sSL https://api.controld.com/dl -o /tmp/ctrld-installer.sh
sudo sh /tmp/ctrld-installer.sh update
```

## 🚨 Emergency Procedures

### DNS Resolution Failure
```bash
# Step 1: Quick restart attempt
sudo controld-maintenance restart

# Step 2: Check system status
sudo controld-maintenance health

# Step 3: Emergency DNS restore
sudo controld-maintenance emergency
```

### Emergency DNS Restore
The emergency restore procedure:
1. Stops ctrld service
2. Restores system DNS to public resolvers (1.1.1.1, 8.8.8.8)  
3. Flushes DNS cache
4. Provides recovery instructions

```bash
# Full emergency restore
sudo controld-maintenance emergency

# Manual emergency fallback  
sudo networksetup -setdnsservers "Wi-Fi" 1.1.1.1 8.8.8.8
sudo dscacheutil -flushcache
```

### Service Recovery
```bash
# If ctrld won't start, check logs
log show --predicate 'process == "ctrld"' --last 10m

# Verify configuration syntax
sudo ctrld run -c /etc/controld/ctrld.toml --dry-run

# Check port conflicts
sudo lsof -i :53
```

## 📈 Optimization

### Performance Tuning
Edit `/etc/controld/ctrld.toml`:

```toml
[upstream.0]
timeout = 3000        # Reduce timeout for faster failover
bootstrap_ip = "NEW"  # Update if Control D infrastructure changes

# For high-traffic environments:
max_conns = 8         # Increase concurrent connections
```

### Cache Optimization
```bash
# Clear system DNS cache
sudo dscacheutil -flushcache
sudo killall -HUP mDNSResponder

# Monitor cache effectiveness
sudo controld-maintenance performance
```

## 📋 Regular Maintenance Tasks

### Weekly Tasks
- [ ] Review performance logs
- [ ] Check for service updates  
- [ ] Verify VPN integration still working
- [ ] Test emergency restore procedure

### Monthly Tasks  
- [ ] Review and clean old backups
- [ ] Update bootstrap IP if needed
- [ ] Review split-DNS rules for optimization
- [ ] Test all domain routing paths

### Quarterly Tasks
- [ ] Full system backup to external location
- [ ] Review and update documentation
- [ ] Performance benchmarking comparison
- [ ] Security audit of configuration

## 🔧 Maintenance Commands Reference

```bash
# System Health & Performance
sudo controld-maintenance health      # Quick health check
sudo controld-maintenance performance # DNS speed test  
sudo controld-maintenance full       # Complete diagnostics

# Service Management
sudo controld-maintenance restart    # Safe service restart
sudo controld-maintenance backup     # Manual configuration backup

# Emergency Procedures  
sudo controld-maintenance emergency  # Emergency DNS restore

# System Verification
nslookup google.com 127.0.0.1       # Test internet domains
dig myapp.test @127.0.0.1           # Test development domains
dig +short whoami.akamai.net @127.0.0.1  # DNS leak test
```

## 📊 Health Monitoring Dashboard

### Key Metrics to Monitor
1. **DNS Query Response Time** - Should be <100ms consistently
2. **Service Uptime** - ctrld process should never crash
3. **Upstream Connections** - 1-2 active connections to Control D
4. **Error Rate** - Zero failed DNS queries under normal conditions  
5. **Memory Usage** - <20MB for ctrld process
6. **DNS Leak Status** - All queries through 127.0.0.1

### Alert Thresholds  
- 🟡 **Warning**: Query time >200ms
- 🟡 **Warning**: >5% query failure rate  
- 🔴 **Critical**: Service down >1 minute
- 🔴 **Critical**: DNS leakage detected
- 🔴 **Critical**: No upstream connectivity

---

> **Best Practice**: Run `sudo controld-maintenance full` weekly to ensure optimal system health and catch any issues early.

> **Pro Tip**: The automated maintenance at 3:00 AM handles 99% of maintenance tasks. Manual intervention is rarely needed with this robust setup.
