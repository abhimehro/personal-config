# AdGuard Import Checklist
## Quick Reference for Your Migration

### ✅ **Pre-Import Verification**

#### File Check:
- [ ] `Consolidated-Denylist.txt` exists in Downloads folder
- [ ] `Consolidated-Allowlist.txt` exists in Downloads folder
- [ ] Files are readable (not corrupted)
- [ ] Files contain expected content (not empty)

#### AdGuard Check:
- [ ] AdGuard for macOS is installed
- [ ] AdGuard is running (icon in menu bar)
- [ ] You have admin privileges
- [ ] Internet connection is stable

---

### 🚀 **Import Process (5 minutes)**

#### Step 1: Import Denylist (2 minutes)
1. [ ] Click AdGuard icon in menu bar
2. [ ] Click gear icon ⚙️ (Preferences)
3. [ ] Click "Filters" tab
4. [ ] Scroll to "Custom" section
5. [ ] Click "+ Add custom filter"
6. [ ] Name: `Comprehensive Tracker Denylist`
7. [ ] Click "Choose File"
8. [ ] Select `Consolidated-Denylist.txt`
9. [ ] Click "Open"
10. [ ] Ensure filter is checked/enabled

#### Step 2: Import Allowlist (2 minutes)
1. [ ] In Preferences, click "Allowlist" tab
2. [ ] Click "Import" button
3. [ ] Select `Consolidated-Allowlist.txt`
4. [ ] Click "Open"
5. [ ] Verify domains appear in allowlist

#### Step 3: Test Configuration (1 minute)
1. [ ] Visit a website (e.g., google.com)
2. [ ] Check AdGuard Statistics tab
3. [ ] Verify some requests are blocked
4. [ ] Confirm website still loads normally

---

### 🔍 **Quick File Verification**

#### Denylist Format Check:
- [ ] File starts with comment lines (#)
- [ ] Contains domain names (one per line)
- [ ] No @@ prefix on domains
- [ ] No empty lines at end

#### Allowlist Format Check:
- [ ] File starts with comment lines (#)
- [ ] All domains have @@ prefix
- [ ] One domain per line
- [ ] No empty lines at end

---

### ⚠️ **Troubleshooting Quick Fixes**

#### If Import Fails:
- [ ] Check file encoding (should be UTF-8)
- [ ] Verify file permissions
- [ ] Try importing smaller test file first
- [ ] Restart AdGuard and try again

#### If Websites Break:
- [ ] Check allowlist is imported correctly
- [ ] Add broken domains to allowlist manually
- [ ] Temporarily disable denylist to test
- [ ] Adjust filter sensitivity if needed

#### If Performance Issues:
- [ ] Monitor system resources
- [ ] Consider reducing list size initially
- [ ] Check AdGuard Statistics for load
- [ ] Restart AdGuard if needed

---

### 📊 **Expected Results**

#### After Successful Import:
- [ ] AdGuard Statistics shows blocked requests
- [ ] Tracker domains are blocked
- [ ] Essential websites work normally
- [ ] System performance is acceptable
- [ ] No false positives on major sites

#### Performance Indicators:
- [ ] Browsing speed is normal
- [ ] AdGuard responds quickly
- [ ] System resources are stable
- [ ] No excessive memory usage

---

### 🎯 **Success Criteria**

Your migration is successful when:
- [ ] All tracker lists are consolidated into two files
- [ ] Both files import without errors
- [ ] AdGuard blocks tracking requests
- [ ] Essential services remain functional
- [ ] System performance is maintained
- [ ] You have comprehensive tracking protection

---

### 📞 **If You Need Help**

1. **Check the detailed guide**: `AdGuard-Import-Guide.md`
2. **Run verification script**: `python3 test-adguard-import.py`
3. **Review troubleshooting section** in the main guide
4. **Check AdGuard logs**: Help → Show Logs
5. **Contact AdGuard support** if needed

---

**🎉 You're ready to migrate from Control D to AdGuard!**
