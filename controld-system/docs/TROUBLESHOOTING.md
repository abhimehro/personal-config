# Control D Troubleshooting - WORKING SYSTEM

This guide covers troubleshooting for the **verified working** Control D configuration.

## 🎯 **Quick Validation Checklist**

Run these commands to verify system is working:

```bash
# 1. Check Raycast extension - should show "Connected"

# 2. Check IP location matches profile expectation
#    Gaming: Should show real location (Baton Rouge, LA)
#    Privacy: Should show masked/different location

# 3. Test Control D connectivity
dig @127.0.0.1 p.controld.com +short
# Should return Control D IP addresses

# 4. Test ad blocking (privacy profile only)
dig @127.0.0.1 doubleclick.net
# Privacy profile: Should return NXDOMAIN with dns.controld.com authority
# Gaming profile: Should return actual IPs (ads allowed)

# 5. Check service status
controld-manager status
```

## 🚨 **Common Issues & Solutions**

### **Issue: Raycast Shows "Disconnected"**
**Symptoms**: Extension shows not connected, IP location shows real location
**Cause**: Service not actually connecting to Control D
**Solution**:
```bash
# Restart current profile
sudo controld-manager switch $(controld-manager status | grep "Active Profile" | awk '{print $3}')

# Verify connectivity after restart
dig @127.0.0.1 p.controld.com +short
```

### **Issue: IP Location Not Changing**
**Symptoms**: Location always shows real location regardless of profile
**Cause**: DNS not routing through Control D properly
**Solution**:
```bash
# Check system DNS configuration
networksetup -getdnsservers Wi-Fi
# Should show: 127.0.0.1

# Reset DNS if incorrect
sudo networksetup -setdnsservers Wi-Fi 127.0.0.1
sudo dscacheutil -flushcache

# Restart current profile
sudo controld-manager switch privacy  # or gaming
```

### **Issue: Profile Switching Fails**
**Symptoms**: Error during profile switch, network connectivity lost
**Solution**:
```bash
# Emergency recovery - restores network immediately
sudo controld-manager emergency

# Wait 10 seconds, then try switch again
sudo controld-manager switch <desired_profile>
```

### **Issue: DNS Resolution Slow/Failing**
**Symptoms**: Websites load slowly, DNS timeouts
**Solution**:
```bash
# Check if service is running
controld-manager status

# If stopped, restart
sudo controld-manager switch gaming  # or privacy

# Test resolution speed
time dig @127.0.0.1 google.com +short
```

### **Issue: Ad Blocking Not Working**
**Symptoms**: Ads still showing with privacy profile
**Solution**:
```bash
# Verify privacy profile is active
controld-manager status

# Test ad blocking directly
dig @127.0.0.1 doubleclick.net
# Should return NXDOMAIN with dns.controld.com authority

# If ads resolve to IPs, switch profiles:
sudo controld-manager switch privacy
```

## 🔧 **System Recovery Procedures**

### **Complete System Reset**
```bash
# 1. Emergency recovery
sudo controld-manager emergency

# 2. Verify network works
ping google.com

# 3. Reinstall if needed
cd ~/Documents/dev/personal-config/controld-system
sudo ./install.sh

# 4. Configure desired profile
sudo controld-manager switch gaming  # or privacy
```

### **Service Won't Start**
```bash
# Check for conflicting processes
ps aux | grep ctrld

# Kill any stuck processes
sudo pkill -f ctrld

# Clear any stuck configurations
sudo rm -f /etc/controld/ctrld.toml

# Restart fresh
sudo controld-manager switch gaming
```

### **Network Completely Broken**
```bash
# Emergency DNS restoration
sudo networksetup -setdnsservers Wi-Fi "Empty"
sudo dscacheutil -flushcache

# Test basic connectivity
ping 8.8.8.8

# If still broken, restart network interface
sudo ifconfig en0 down && sudo ifconfig en0 up
```

## ⚠️ **AVOID These Broken Approaches**

❌ **Don't use DOH3**: Causes silent failures and false positives
❌ **Don't use LaunchDaemon**: Creates conflicts with working system  
❌ **Don't manually edit TOML files**: Breaks Control D authentication
❌ **Don't use complex monitoring**: Adds unnecessary failure points

## ✅ **Verification Commands**

Use these to confirm the system is working correctly:

```bash
# Control D connectivity (should return IPs)
dig @127.0.0.1 p.controld.com +short

# Privacy profile ad blocking (should return NXDOMAIN)
dig @127.0.0.1 doubleclick.net | grep -E "(NXDOMAIN|dns.controld.com)"

# Gaming profile ad allowing (should return IPs)
dig @127.0.0.1 doubleclick.net +short | head -3

# System DNS configuration (should be 127.0.0.1)
networksetup -getdnsservers Wi-Fi

# Service process (should be running)
ps aux | grep ctrld | grep -v grep

# Protocol verification (should be doh, not doh3)
sudo grep "type = " /etc/controld/ctrld.toml
```

## 📞 **Getting Help**

If issues persist after following this guide:

1. **Document the problem**:
   - Copy output from verification commands above
   - Note specific error messages
   - Describe what you were trying to do

2. **Run emergency recovery**:
   ```bash
   sudo controld-manager emergency
   ```

3. **Provide system state**:
   ```bash
   controld-manager status
   cat verification/working_system_state.txt
   ```

Remember: This system has been extensively tested and verified. Most issues are due to network changes or service conflicts, not configuration problems.
