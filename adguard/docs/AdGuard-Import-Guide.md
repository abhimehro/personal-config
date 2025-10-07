# AdGuard macOS Import Guide
## Step-by-Step Instructions for Your Consolidated Lists

### 🎯 **Pre-Import Checklist**
- [ ] AdGuard for macOS is installed and running
- [ ] Your consolidated files are ready in `/Users/abhimehrotra/Downloads/`
- [ ] You have administrator access on your Mac
- [ ] Backup any existing AdGuard settings (optional but recommended)

---

## 📋 **Step 1: Import the Denylist (Blocking Rules)**

### 1.1 Open AdGuard Preferences
- Click the **AdGuard icon** in your Mac's menu bar (top right)
- Select the **gear icon** ⚙️ to open **Preferences**

### 1.2 Navigate to Filters
- Click on the **"Filters"** tab in the preferences window
- Scroll down to find the **"Custom"** section

### 1.3 Add Custom Denylist
- Click **"+ Add custom filter"** or **"Add custom filter"**
- In the dialog box that appears:
  - **Name**: `Comprehensive Tracker Denylist`
  - **URL**: Leave blank (we'll import from file)
  - Click **"Choose File"** or **"Browse"**
  - Navigate to `/Users/abhimehrotra/Downloads/`
  - Select `Consolidated-Denylist.txt`
  - Click **"Open"**

### 1.4 Enable the Filter
- Ensure the new filter is **checked/enabled**
- The filter should show as active in your Custom filters list

---

## 📋 **Step 2: Import the Allowlist (Bypass Rules)**

### 2.1 Navigate to Allowlist
- In AdGuard Preferences, click the **"Allowlist"** tab
- This is separate from the Filters section

### 2.2 Import Allowlist File
- Click the **"Import"** button (usually near the top)
- Navigate to `/Users/abhimehrotra/Downloads/`
- Select `Consolidated-Allowlist.txt`
- Click **"Open"**

### 2.3 Verify Import
- You should see all the domains with `@@` prefix in your allowlist
- The count should match your consolidated allowlist

---

## 📋 **Step 3: Configure AdGuard Settings**

### 3.1 DNS Settings (Optional)
- Go to **"DNS"** tab in AdGuard Preferences
- Consider enabling **"Use custom DNS servers"**
- Recommended servers:
  - `1.1.1.1` (Cloudflare)
  - `8.8.8.8` (Google)

### 3.2 Stealth Mode
- Go to **"Stealth Mode"** tab
- Enable options as desired:
  - ✅ Remove tracking parameters
  - ✅ Hide your search queries
  - ✅ Block WebRTC

### 3.3 User Rules (Optional)
- Go to **"User Rules"** tab
- Add any custom rules if needed

---

## 📋 **Step 4: Test Your Configuration**

### 4.1 Test Blocking
- Visit a website known to have trackers
- Check AdGuard's **"Statistics"** tab to see blocked requests
- Verify tracker domains are being blocked

### 4.2 Test Allowlist
- Visit a site that should work normally
- Ensure essential services aren't broken
- Check that allowlisted domains are accessible

### 4.3 Monitor Performance
- Watch system performance after import
- Large lists may take a moment to load initially

---

## 🔧 **Troubleshooting Common Issues**

### Issue 1: Filter Not Loading
**Solution:**
- Ensure file is UTF-8 encoded
- Check file permissions
- Try importing a smaller test file first

### Issue 2: Too Many Domains
**Solution:**
- Start with a subset of domains
- Gradually increase the list size
- Monitor system performance

### Issue 3: False Positives
**Solution:**
- Add problematic domains to allowlist
- Adjust filter sensitivity if needed

### Issue 4: Import Errors
**Solution:**
- Verify file format (one domain per line)
- Check for special characters
- Ensure no empty lines at file end

---

## 📊 **Expected Results After Import**

### Denylist Performance:
- **Blocked Requests**: Should see significant increase in blocked tracking requests
- **Coverage**: Comprehensive protection against all specified trackers
- **Performance**: Minimal impact on browsing speed

### Allowlist Performance:
- **Essential Services**: Should remain functional
- **Bypass Rules**: Legitimate domains should load normally
- **Balance**: Proper blocking without breaking functionality

---

## 🚀 **Advanced Configuration (Optional)**

### Custom DNS Integration:
- If you want to maintain some Control D functionality
- Configure custom DNS servers in AdGuard
- Use Control D's DNS addresses if preferred

### Periodic Updates:
- Set up reminders to update your consolidated lists
- Consider automating the consolidation process
- Monitor for new tracker domains

---

## 📞 **Getting Help**

If you encounter issues:

1. **Check AdGuard Logs**: Go to Help → Show Logs
2. **Reset if Needed**: Help → Reset Settings (backup first!)
3. **AdGuard Support**: https://adguard.com/en/support.html
4. **Community Forum**: https://forum.adguard.com/

---

## ✅ **Final Verification Checklist**

- [ ] Denylist imported and active
- [ ] Allowlist imported and active
- [ ] AdGuard is blocking trackers (check Statistics)
- [ ] Essential websites still work
- [ ] System performance is acceptable
- [ ] Backup of settings created

---

**🎉 Congratulations!** You've successfully migrated from Control D DNS profiles to AdGuard with comprehensive tracking protection!
